from datetime import date, time
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from plataforma.models import Empresa
from inspecao_ai.chat_services import normalizar_json_chat
from inspecao_ai.domain_logic import (
    construir_memoria_operacional_furo,
    construir_resumo_validacao_analise,
    construir_sugestoes_reprocessamento,
    filtrar_analises_visiveis,
    nome_base_analise_reprocessada,
    parse_zone_payload,
)
from inspecao_ai.services.biblioteca import construir_contexto_biblioteca
from inspecao_ai.services.box_pipeline import construir_zonas_caixa, determinar_marcador
from inspecao_ai.services.dataset_quality import construir_contexto_qualidade_dataset
from inspecao_ai.services.ocr_core import extract_crop, extract_metric_value, safe_detection_text
from inspecao_ai.services.report_layout import resolver_bbox_percentual
from inspecao_ai.services.training_examples import construir_entrada_modelo
from inspecao_ai.services.training_examples import sincronizar_exemplos_validacao
from inspecao_ai.models import AnaliseImagemAI, ExemploTreinoAI
from inspecao_ai.services import executar_analise_imagem
from inspecao_ai.workflows import guardar_correcoes_campos


class AnaliseZonePayloadTests(SimpleTestCase):
    def test_parse_zone_payload_limpa_zona_unica(self):
        zone = parse_zone_payload(
            '{"x_percent": 10.126, "y_percent": 20, "w_percent": 30, "h_percent": 40, "name": "Área central"}',
            single=True,
        )

        self.assertEqual(
            zone,
            {
                "x_percent": 10.13,
                "y_percent": 20.0,
                "w_percent": 30.0,
                "h_percent": 40.0,
                "name": "Área central",
            },
        )

    def test_parse_zone_payload_rejeita_zona_fora_dos_limites(self):
        with self.assertRaisesMessage(ValueError, "Zona fora dos limites."):
            parse_zone_payload(
                '[{"x_percent": 80, "y_percent": 10, "w_percent": 30, "h_percent": 20}]',
                single=False,
            )


class AnaliseValidationSummaryTests(SimpleTestCase):
    def test_resumo_validacao_compara_valores_normalizados_e_sugere_reprocessamento(self):
        analise = SimpleNamespace(
            tipo_documento="relatorio_trabalhador",
            campos_extraidos={
                "campos": [
                    {
                        "campo_semantico": "data",
                        "valor_lido": "22/05/2026",
                        "valor_validado": "22/05/2026",
                        "validado_utilizador": True,
                    },
                    {
                        "campo_semantico": "turno",
                        "valor_lido": "Manha",
                        "valor_validado": "Noite",
                        "validado_utilizador": True,
                    },
                    {
                        "campo_semantico": "equipa",
                        "valor_lido": "Equipa A",
                        "valor_validado": "",
                        "validado_utilizador": False,
                    },
                ]
            },
        )

        resumo = construir_resumo_validacao_analise(analise)
        sugestoes = construir_sugestoes_reprocessamento(analise, resumo)

        self.assertEqual(resumo["total_validados"], 2)
        self.assertEqual(resumo["total_acertos"], 1)
        self.assertEqual(resumo["total_falhas"], 1)
        self.assertEqual(resumo["taxa_acerto"], 50.0)
        self.assertEqual(resumo["campos"][0]["comparacao_estado"], "acertou")
        self.assertEqual(resumo["campos"][1]["comparacao_estado"], "falhou")
        self.assertEqual(sugestoes[0]["focus"], "turno")

    def test_nome_base_remove_sufixos_de_reprocessamento(self):
        self.assertEqual(
            nome_base_analise_reprocessada("Relatório Turno 4 · Data · reprocessada"),
            "Relatório Turno 4",
        )


class AnaliseVisibilityTests(SimpleTestCase):
    def test_preview_nao_guardada_nao_aparece_no_historico(self):
        analises = [
            SimpleNamespace(metadados={"opcoes_entrada": {"preview_mode": True}}, guardada=False),
            SimpleNamespace(metadados={"opcoes_entrada": {"preview_mode": True}}, guardada=True),
            SimpleNamespace(metadados={}, guardada=False),
        ]

        self.assertEqual(filtrar_analises_visiveis(analises), analises[1:])


class MemoriaOperacionalAITests(SimpleTestCase):
    def test_memoria_furo_compila_destaques_e_texto(self):
        projeto = SimpleNamespace(pk="projeto-1", nome="Projeto Serra")
        furo = SimpleNamespace(
            pk="furo-1",
            nome="Furo 101",
            projeto=projeto,
            estado="ativo",
            get_estado_display=lambda: "Ativo",
            data=None,
            localizacao="Serra Norte",
            local_sondagem="S1",
            latitude=41.1,
            longitude=-8.6,
            profundidade=120,
            profundidade_maxima_atingida=98,
            total_despesas_diretas=Decimal("1250.50"),
            total_medicoes_registadas=3,
            observacoes="Zona fraturada",
        )

        memoria = construir_memoria_operacional_furo(furo)

        self.assertEqual(memoria["projeto_nome"], "Projeto Serra")
        self.assertIn("Com coordenadas", memoria["destaques"])
        self.assertIn("Despesas diretas acumuladas: 1250.50", memoria["texto_memoria"])
        self.assertIn("Observações: Zona fraturada", memoria["texto_memoria"])


class ChatJsonNormalizationTests(SimpleTestCase):
    def test_normalizar_json_chat_converte_tipos_persistiveis(self):
        resultado = normalizar_json_chat(
            {
                Decimal("10.5"): {
                    "data": date(2026, 5, 22),
                    "hora": time(8, 30),
                    "valores": {Decimal("1.25"), Decimal("2.50")},
                }
            }
        )

        self.assertEqual(set(resultado.keys()), {"10.5"})
        self.assertEqual(resultado["10.5"]["data"], "2026-05-22")
        self.assertEqual(resultado["10.5"]["hora"], "08:30:00")
        self.assertCountEqual(resultado["10.5"]["valores"], [1.25, 2.5])


class BibliotecaAITests(SimpleTestCase):
    def test_contexto_biblioteca_filtra_e_resume_documentos(self):
        documentos = [
            {"extensao": ".pdf", "leitura": "txt_auxiliar", "tem_txt": True},
            {"extensao": ".pdf", "leitura": "nao_preparado", "tem_txt": False},
            {"extensao": ".md", "leitura": "direta", "tem_txt": False},
        ]

        contexto = construir_contexto_biblioteca(
            documentos=documentos,
            filtro_leitura="txt_auxiliar",
            filtro_extensao=".pdf",
        )

        self.assertEqual(contexto["documentos"], [documentos[0]])
        self.assertEqual(contexto["total_documentos"], 1)
        self.assertEqual(contexto["total_pdfs_com_txt"], 1)
        self.assertEqual(contexto["extensoes_disponiveis"], [".md", ".pdf"])


class OcrCoreTests(SimpleTestCase):
    def test_extract_metric_value_normaliza_intervalo_em_metros(self):
        self.assertEqual(extract_metric_value(" 10,5 - 12M "), "10.5-12m")

    def test_extract_crop_limita_bbox_a_imagem(self):
        imagem = Image.new("RGB", (20, 10), "white")

        crop = extract_crop(
            imagem,
            {"x_min": -5, "y_min": 3, "x_max": 40, "y_max": 20},
        )

        self.assertEqual(crop.size, (20, 7))

    def test_safe_detection_text_trunca_payload_longo(self):
        self.assertEqual(safe_detection_text("abcdef", max_length=5), "abcd…")


class BoxPipelineTests(SimpleTestCase):
    def test_construir_zonas_caixa_gera_zonas_para_quatro_filas(self):
        zonas = construir_zonas_caixa(largura=1000, altura=400)

        self.assertEqual(len(zonas), 36)
        self.assertEqual({zona["fila"] for zona in zonas}, {1, 2, 3, 4})
        self.assertEqual(zonas[0]["tipo_zona"], "ponta_inicial")

    def test_determinar_marcador_classifica_mistura_equilibrada(self):
        self.assertEqual(determinar_marcador(pontos_azul=10, pontos_preto=8), "misto")
        self.assertEqual(determinar_marcador(pontos_azul=10, pontos_preto=1), "azul")


class ReportPipelineLayoutTests(SimpleTestCase):
    def test_resolver_bbox_percentual_converte_zona_para_pixels(self):
        bbox = resolver_bbox_percentual(
            1000,
            500,
            {"x_percent": 10, "y_percent": 20, "w_percent": 30, "h_percent": 40},
        )

        self.assertEqual(bbox, {"x_min": 100, "y_min": 100, "x_max": 400, "y_max": 300})


class ImagePipelineDispatchTests(SimpleTestCase):
    @patch("inspecao_ai.services.analisar_relatorio")
    def test_relatorio_e_despachado_para_pipeline_proprio(self, analisar_relatorio):
        analise = SimpleNamespace(imagem_original=True, tipo_documento="relatorio_trabalhador")
        analisar_relatorio.return_value = analise

        resultado = executar_analise_imagem(analise)

        self.assertIs(resultado, analise)
        analisar_relatorio.assert_called_once_with(analise)

    @patch("inspecao_ai.services.analisar_caixa_cilindrica")
    def test_caixa_e_despachada_para_pipeline_proprio(self, analisar_caixa):
        analise = SimpleNamespace(imagem_original=True, tipo_documento="caixa_cilindrica")
        analisar_caixa.return_value = analise

        resultado = executar_analise_imagem(analise)

        self.assertIs(resultado, analise)
        analisar_caixa.assert_called_once_with(analise)


class TrainingExampleTests(SimpleTestCase):
    def test_construir_entrada_modelo_preserva_contexto_da_previsao(self):
        analise = SimpleNamespace(pk="analise-1", tipo_documento="relatorio_trabalhador", motor_analise="vision_v2")
        campo = {
            "campo": "Data",
            "campo_semantico": "data",
            "tipo_conteudo": "manual",
            "valor_lido": "23/05/2026",
            "confianca": 0.91,
            "ocr_aceite": True,
        }

        entrada = construir_entrada_modelo(analise=analise, campo=campo, indice_campo=2)

        self.assertEqual(entrada["campo_semantico"], "data")
        self.assertEqual(entrada["valor_previsto"], "23/05/2026")
        self.assertEqual(entrada["motor_analise"], "vision_v2")
        self.assertEqual(entrada["indice_campo"], 2)

    @patch("inspecao_ai.workflows.sincronizar_exemplos_validacao")
    def test_guardar_correcao_dispara_criacao_de_exemplos_rotulados(self, sincronizar):
        analise = SimpleNamespace(
            campos_extraidos={"campos": [{"campo_semantico": "data", "valor_lido": "22/05/2026"}]},
            save=Mock(),
        )
        utilizador = object()

        guardar_correcoes_campos(
            analise,
            {"campo_validado_0": "23/05/2026"},
            utilizador=utilizador,
        )

        self.assertTrue(analise.campos_extraidos["campos"][0]["validado_utilizador"])
        sincronizar.assert_called_once_with(
            analise=analise,
            campos=analise.campos_extraidos["campos"],
            utilizador=utilizador,
        )


class DatasetQualityTests(SimpleTestCase):
    def test_revisao_historica_nao_bloqueia_baseline_com_volume_suficiente(self):
        exemplos = [
            {
                "analise_id": f"analise-{indice}",
                "analise__nome": f"Relatorio {indice}",
                "tipo_documento": "relatorio_trabalhador",
                "campo_semantico": "data",
                "indice_campo": 0,
                "ativo": True,
                "rotulo_validado": f"23/05/{indice:04d}",
                "acertou_previsao": True,
            }
            for indice in range(30)
        ]
        exemplos.append(
            {
                "analise_id": "analise-0",
                "analise__nome": "Relatorio 0",
                "tipo_documento": "relatorio_trabalhador",
                "campo_semantico": "data",
                "indice_campo": 0,
                "ativo": False,
                "rotulo_validado": "22/05/2000",
                "acertou_previsao": False,
            }
        )

        contexto = construir_contexto_qualidade_dataset(exemplos)

        self.assertEqual(contexto["total_ativos"], 30)
        self.assertEqual(contexto["total_revisoes"], 1)
        self.assertEqual(contexto["total_conflitos"], 0)
        self.assertTrue(contexto["pronto_baseline"])
        self.assertEqual(sum(contexto["split_sugerido"].values()), 30)

    def test_conflitos_ativos_bloqueiam_baseline(self):
        exemplos = [
            {
                "analise_id": f"analise-{indice}",
                "analise__nome": f"Relatorio {indice}",
                "tipo_documento": "relatorio_trabalhador",
                "campo_semantico": "data",
                "indice_campo": 0,
                "ativo": True,
                "rotulo_validado": "23/05/2026",
                "acertou_previsao": True,
            }
            for indice in range(30)
        ]
        exemplos.append({**exemplos[0], "rotulo_validado": "24/05/2026"})

        contexto = construir_contexto_qualidade_dataset(exemplos)

        self.assertEqual(contexto["total_conflitos"], 1)
        self.assertFalse(contexto["pronto_baseline"])


class TrainingExamplePersistenceTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()

    def tearDown(self):
        self.media_override.disable()
        self.media_dir.cleanup()

    def test_nova_correcao_versiona_rotulo_e_desativa_versao_anterior(self):
        empresa = Empresa.objects.create(nome="Empresa Dataset")
        imagem = BytesIO()
        Image.new("RGB", (10, 10), "white").save(imagem, format="PNG")
        imagem.seek(0)
        analise = AnaliseImagemAI.objects.create(
            empresa=empresa,
            nome="Relatorio 001",
            tipo_documento="relatorio_trabalhador",
            imagem_original=SimpleUploadedFile("relatorio-001.png", imagem.read(), content_type="image/png"),
        )
        campo = {
            "campo_semantico": "data",
            "valor_lido": "22/05/2026",
            "valor_validado": "23/05/2026",
            "validado_utilizador": True,
        }

        sincronizar_exemplos_validacao(analise=analise, campos=[campo])
        campo["valor_validado"] = "24/05/2026"
        sincronizar_exemplos_validacao(analise=analise, campos=[campo])

        exemplos = list(ExemploTreinoAI.objects.filter(analise=analise).order_by("versao_rotulo"))
        self.assertEqual([item.versao_rotulo for item in exemplos], [1, 2])
        self.assertFalse(exemplos[0].ativo)
        self.assertTrue(exemplos[1].ativo)
        self.assertEqual(exemplos[1].rotulo_validado, "24/05/2026")
