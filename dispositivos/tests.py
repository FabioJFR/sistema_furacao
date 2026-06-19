from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dispositivos.models import Dispositivo, LeituraBrutaDispositivo, SurveyShot
from dispositivos.drivers.magcruiser.parser import parse_magcruiser_payload
from dispositivos.services.dashboard_page import construir_contexto_dashboard_dispositivos
from dispositivos.services.dashboard_capture import processar_criacao_sessao_captura
from dispositivos.services.api_flow import construir_resposta_operacao_api
from dispositivos.services.ingestao import guardar_leitura_dispositivo
from dispositivos.services.magcruiser_import import gravar_importacao_magcruiser, parse_magcruiser_file
from dispositivos.services.sessao import (
    _validar_dispositivo_empresa,
    _validar_empregado_empresa,
    _validar_furo_empresa,
    criar_sessao_dispositivo,
    ler_dispositivo_uma_vez,
)
from projetos.models import Furo, Medicao
from projetos.tests.helpers import criar_empresa, criar_empregado, criar_furo, criar_projeto, criar_user


class MagCruiserPayloadParserTests(SimpleTestCase):
    def test_parse_payload_extrai_medicao_e_metadados_opcionais(self):
        resultado = parse_magcruiser_payload(
            "DEPTH=120.50;INC=-65.20;AZI=182.10;MAG=44.20;TEMP=23.50;HOLE=F-101"
        )

        self.assertEqual(resultado["profundidade"], Decimal("120.50"))
        self.assertEqual(resultado["inclinacao"], Decimal("-65.20"))
        self.assertEqual(resultado["azimute"], Decimal("182.10"))
        self.assertEqual(resultado["magnetismo"], Decimal("44.20"))
        self.assertEqual(resultado["temperatura"], Decimal("23.50"))
        self.assertEqual(resultado["nome_furo"], "F-101")

    def test_parse_payload_ignora_segmentos_sem_chave_valor(self):
        resultado = parse_magcruiser_payload(
            "ruido;DEPTH=10;INC=-2;AZI=90;outro_ruido"
        )

        self.assertEqual(resultado["profundidade"], Decimal("10"))
        self.assertIsNone(resultado["magnetismo"])
        self.assertIsNone(resultado["temperatura"])


class MagCruiserFileParserTests(SimpleTestCase):
    def test_parse_csv_normaliza_colunas_e_preview(self):
        uploaded = SimpleUploadedFile(
            "leituras.csv",
            b"hole;depth;inc;azi;mag;temp\nF-101;10,5;-2,5;90;44,2;22\n",
            content_type="text/csv",
        )

        resultado = parse_magcruiser_file(uploaded)
        row = resultado["rows"][0]

        self.assertEqual(resultado["formato"], "csv")
        self.assertEqual(resultado["total_linhas"], 1)
        self.assertEqual(resultado["preview_rows"], resultado["rows"])
        self.assertEqual(row["hole_name"], "F-101")
        self.assertEqual(row["depth"], Decimal("10.5"))
        self.assertEqual(row["inc"], Decimal("-2.5"))
        self.assertEqual(row["azi"], Decimal("90"))
        self.assertEqual(row["mag"], Decimal("44.2"))
        self.assertEqual(row["temp"], Decimal("22"))

    def test_parse_xlsx_normaliza_colunas_e_preview(self):
        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["furo", "profundidade", "inclinacao", "azimute", "magnetismo", "temperatura"])
        sheet.append(["F-201", "15,5", "-4,5", 185, "43,1", 23])
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        uploaded = SimpleUploadedFile(
            "leituras.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        resultado = parse_magcruiser_file(uploaded)
        row = resultado["rows"][0]

        self.assertEqual(resultado["formato"], "xlsx")
        self.assertEqual(resultado["total_linhas"], 1)
        self.assertEqual(resultado["preview_rows"], resultado["rows"])
        self.assertEqual(row["hole_name"], "F-201")
        self.assertEqual(row["depth"], Decimal("15.5"))
        self.assertEqual(row["inc"], Decimal("-4.5"))
        self.assertEqual(row["azi"], Decimal("185"))
        self.assertEqual(row["mag"], Decimal("43.1"))
        self.assertEqual(row["temp"], Decimal("23"))

    def test_parse_las_extrai_ascii_validas(self):
        uploaded = SimpleUploadedFile(
            "leituras.las",
            b"~Version\nVERS. 2.0\n~A\n10.0 -2.0 90.0 44.0\n20.0 -3.0 91.0\n",
            content_type="text/plain",
        )

        resultado = parse_magcruiser_file(uploaded)

        self.assertEqual(resultado["formato"], "las")
        self.assertEqual(resultado["total_linhas"], 2)
        self.assertEqual(resultado["rows"][1]["depth"], Decimal("20.0"))
        self.assertIsNone(resultado["rows"][1]["mag"])

    def test_parse_csv_rejeita_ficheiro_sem_linhas_validas(self):
        uploaded = SimpleUploadedFile(
            "invalido.csv",
            b"hole;depth;inc\nF-101;10;-2\n",
            content_type="text/csv",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Não foi possível extrair linhas válidas.",
        ):
            parse_magcruiser_file(uploaded)

    def test_parse_csv_rejeita_lote_com_profundidade_negativa(self):
        uploaded = SimpleUploadedFile(
            "profundidade-negativa.csv",
            b"hole;depth;inc;azi\nF-101;-1;-2;90\n",
            content_type="text/csv",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "profundidade não pode ser negativa",
        ):
            parse_magcruiser_file(uploaded)

    def test_parse_csv_rejeita_lote_com_angulos_fora_do_intervalo(self):
        uploaded = SimpleUploadedFile(
            "angulos-invalidos.csv",
            b"hole;depth;inc;azi\nF-101;10;-95;361\n",
            content_type="text/csv",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "inclinação deve estar entre -90 e 90 graus",
        ):
            parse_magcruiser_file(uploaded)

    def test_parse_csv_rejeita_lote_com_profundidade_duplicada_por_furo(self):
        uploaded = SimpleUploadedFile(
            "duplicados.csv",
            b"hole;depth;inc;azi\nF-101;10;-2;90\nF-101;10;-3;91\nF-102;10;-4;92\n",
            content_type="text/csv",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "profundidade duplicada",
        ):
            parse_magcruiser_file(uploaded)


class DispositivoApiFlowTests(SimpleTestCase):
    def test_resposta_operacao_api_preserva_payload_de_sucesso(self):
        resultado = construir_resposta_operacao_api(
            resultado={"ok": True, "eventos": ["usb_ligado"], "valor": "capturado"},
            payload_sucesso=lambda data: {"valor": data["valor"]},
            mensagem_erro_padrao="Falhou.",
        )

        self.assertEqual(resultado["status"], 200)
        self.assertEqual(resultado["payload"], {"valor": "capturado"})
        self.assertEqual(resultado["eventos"], ["usb_ligado"])

    def test_resposta_operacao_api_preserva_status_e_eventos_de_erro(self):
        resultado = construir_resposta_operacao_api(
            resultado={"ok": False, "status": 503, "eventos": ["porta_indisponivel"]},
            mensagem_erro_padrao="Dispositivo indisponível.",
        )

        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["status"], 503)
        self.assertEqual(resultado["eventos"], ["porta_indisponivel"])
        self.assertEqual(resultado["mensagem_erro"], "Dispositivo indisponível.")


class SessaoDispositivoValidationTests(SimpleTestCase):
    def test_rejeita_empregado_sem_empresa(self):
        with self.assertRaisesMessage(
            ValidationError,
            "O utilizador autenticado não está associado a um empregado com empresa válida.",
        ):
            _validar_empregado_empresa(SimpleNamespace(empresa_id=None))

    def test_rejeita_dispositivo_de_outra_empresa(self):
        empregado = SimpleNamespace(empresa_id="empresa-a")
        dispositivo = SimpleNamespace(empresa_id="empresa-b")

        with self.assertRaisesMessage(
            ValidationError,
            "O dispositivo não pertence à empresa do empregado autenticado.",
        ):
            _validar_dispositivo_empresa(dispositivo, empregado)

    def test_rejeita_furo_de_outra_empresa(self):
        empregado = SimpleNamespace(empresa_id="empresa-a")
        furo = SimpleNamespace(empresa_id="empresa-b")

        with self.assertRaisesMessage(
            ValidationError,
            "O furo não pertence à empresa do empregado autenticado.",
        ):
            _validar_furo_empresa(furo, empregado)


class SessaoDispositivoPersistenceTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Dispositivos")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Dispositivos")
        self.furo = criar_furo(
            empresa=self.empresa,
            projeto=self.projeto,
            nome="Furo Dispositivos",
            profundidade_alvo_inicial=250,
            profundidade_alvo_atual=250,
        )
        self.empregado = criar_empregado(
            empresa=self.empresa,
            nome="Operador MagCruiser",
        )
        self.dispositivo = Dispositivo.objects.create(
            empresa=self.empresa,
            nome="MagCruiser USB",
            tipo="magcruiser",
            canal="usb_serial",
            porta="/dev/ttyUSB0",
            baudrate=115200,
            ativo=True,
        )

    def test_processar_criacao_sessao_captura_cria_sessao_real(self):
        resultado = processar_criacao_sessao_captura(
            empresa_id=self.empresa.pk,
            empregado=self.empregado,
            dispositivo_id=self.dispositivo.pk,
            furo_id=self.furo.pk,
        )

        self.assertTrue(resultado["ok"])
        sessao = resultado["sessao"]
        self.assertEqual(sessao.empresa, self.empresa)
        self.assertEqual(sessao.dispositivo, self.dispositivo)
        self.assertEqual(sessao.furo, self.furo)
        self.assertEqual(sessao.empregado, self.empregado)
        self.assertEqual(sessao.status, "criada")

    def test_guardar_leitura_dispositivo_cria_leitura_shot_medicao_e_incrementa_sequencia(self):
        sessao = criar_sessao_dispositivo(
            dispositivo=self.dispositivo,
            furo=self.furo,
            empregado=self.empregado,
        )

        primeiro = guardar_leitura_dispositivo(
            sessao=sessao,
            raw_payload="DEPTH=12.50;INC=-3.20;AZI=181.00;MAG=44.20;TEMP=21.00",
        )
        segundo = guardar_leitura_dispositivo(
            sessao=sessao,
            raw_payload="DEPTH=13.50;INC=-3.40;AZI=182.00;MAG=44.30;TEMP=21.50",
        )

        self.assertEqual(primeiro["leitura"].sequencia, 1)
        self.assertEqual(segundo["leitura"].sequencia, 2)
        self.assertEqual(LeituraBrutaDispositivo.objects.filter(sessao=sessao).count(), 2)
        self.assertEqual(SurveyShot.objects.filter(sessao=sessao, furo=self.furo).count(), 2)
        self.assertEqual(Medicao.objects.filter(furo=self.furo, empresa=self.empresa).count(), 2)
        self.assertEqual(segundo["leitura"].payload_json["profundidade"], "13.50")
        self.assertEqual(segundo["shot"].temperatura, Decimal("21.50"))
        self.assertEqual(segundo["medicao"].profundidade_medida, Decimal("13.50"))

    @patch("dispositivos.services.sessao.construir_driver")
    def test_ler_dispositivo_uma_vez_guarda_dados_e_encerra_sessao(self, construir_driver_mock):
        driver = Mock()
        driver.read_once.return_value = "DEPTH=20.00;INC=-5.00;AZI=180.00;MAG=42.00;TEMP=19.00"
        construir_driver_mock.return_value = driver
        sessao = criar_sessao_dispositivo(
            dispositivo=self.dispositivo,
            furo=self.furo,
            empregado=self.empregado,
        )

        resultado = ler_dispositivo_uma_vez(sessao=sessao)

        sessao.refresh_from_db()
        driver.connect.assert_called_once()
        driver.disconnect.assert_called_once()
        self.assertEqual(sessao.status, "encerrada")
        self.assertIsNotNone(sessao.terminado_em)
        self.assertEqual(resultado["dados"]["profundidade"], Decimal("20.00"))
        self.assertEqual(LeituraBrutaDispositivo.objects.filter(sessao=sessao).count(), 1)
        self.assertEqual(SurveyShot.objects.filter(sessao=sessao).count(), 1)
        self.assertEqual(Medicao.objects.filter(furo=self.furo).count(), 1)

    @patch("dispositivos.services.sessao.construir_driver")
    def test_ler_dispositivo_uma_vez_marca_erro_quando_hardware_falha(self, construir_driver_mock):
        driver = Mock()
        driver.connect.side_effect = RuntimeError("porta indisponível")
        construir_driver_mock.return_value = driver
        sessao = criar_sessao_dispositivo(
            dispositivo=self.dispositivo,
            furo=self.furo,
            empregado=self.empregado,
        )

        with self.assertRaisesMessage(ValidationError, "porta indisponível"):
            ler_dispositivo_uma_vez(sessao=sessao)

        sessao.refresh_from_db()
        driver.disconnect.assert_called_once()
        self.assertEqual(sessao.status, "erro")
        self.assertEqual(sessao.mensagem_erro, "porta indisponível")
        self.assertEqual(LeituraBrutaDispositivo.objects.filter(sessao=sessao).count(), 0)

    def test_gravar_importacao_reconcilia_nome_furo_normalizado_sem_criar_duplicado(self):
        furo_reconciliado = criar_furo(
            empresa=self.empresa,
            projeto=self.projeto,
            nome="Furo 001",
            profundidade_alvo_inicial=100,
            profundidade_alvo_atual=100,
        )
        sessao = criar_sessao_dispositivo(
            dispositivo=self.dispositivo,
            furo=furo_reconciliado,
            empregado=self.empregado,
        )

        resultado = gravar_importacao_magcruiser(
            sessao=sessao,
            rows=[
                {
                    "hole_name": "FURO-1",
                    "depth": Decimal("10"),
                    "inc": Decimal("-2"),
                    "azi": Decimal("90"),
                    "mag": None,
                    "temp": None,
                },
                {
                    "hole_name": "Furo Desconhecido",
                    "depth": Decimal("12"),
                    "inc": Decimal("-3"),
                    "azi": Decimal("91"),
                    "mag": None,
                    "temp": None,
                },
            ],
            modo_aplicacao="all_existing",
        )

        self.assertEqual(resultado["total_gravadas"], 1)
        self.assertEqual(resultado["total_ignoradas"], 1)
        self.assertEqual(resultado["furos_sem_match"], ["Furo Desconhecido"])
        self.assertEqual(SurveyShot.objects.filter(furo=furo_reconciliado).count(), 1)
        self.assertFalse(Furo.objects.filter(empresa=self.empresa, nome="FURO-1").exists())

    def test_dashboard_observabilidade_calcula_disponibilidade_erros_e_latencia(self):
        sessao_ok = criar_sessao_dispositivo(
            dispositivo=self.dispositivo,
            furo=self.furo,
            empregado=self.empregado,
        )
        guardar_leitura_dispositivo(
            sessao=sessao_ok,
            raw_payload="DEPTH=14.00;INC=-3.20;AZI=181.00",
        )
        agora = timezone.now()
        sessao_ok.iniciado_em = agora - timedelta(seconds=20)
        sessao_ok.terminado_em = agora
        sessao_ok.status = "encerrada"
        sessao_ok.save(update_fields=["iniciado_em", "terminado_em", "status"])

        sessao_erro = criar_sessao_dispositivo(
            dispositivo=self.dispositivo,
            furo=self.furo,
            empregado=self.empregado,
        )
        sessao_erro.status = "erro"
        sessao_erro.mensagem_erro = "porta indisponível"
        sessao_erro.save(update_fields=["status", "mensagem_erro"])

        contexto = construir_contexto_dashboard_dispositivos(empresa_id=self.empresa.pk)
        linha = contexto["observabilidade_dispositivos"][0]

        self.assertEqual(linha["dispositivo"], self.dispositivo)
        self.assertEqual(linha["total_sessoes"], 2)
        self.assertEqual(linha["total_erros"], 1)
        self.assertEqual(linha["total_leituras"], 1)
        self.assertEqual(linha["disponibilidade_percentual"], 50)
        self.assertEqual(linha["latencia_media_segundos"], 20)
        self.assertEqual(linha["latencia_media_label"], "20s")


class DispositivoApiEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.empresa = criar_empresa(nome="Empresa API Dispositivos")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto API Dispositivos")
        self.furo = criar_furo(
            empresa=self.empresa,
            projeto=self.projeto,
            nome="Furo API Dispositivos",
            profundidade_alvo_inicial=180,
            profundidade_alvo_atual=180,
        )
        self.user = criar_user(username="operador_api_dispositivos")
        self.empregado = criar_empregado(
            empresa=self.empresa,
            nome="Operador API Dispositivos",
            user=self.user,
        )
        self.dispositivo = Dispositivo.objects.create(
            empresa=self.empresa,
            nome="MagCruiser API",
            tipo="magcruiser",
            canal="usb_serial",
            porta="/dev/ttyUSB1",
            baudrate=115200,
            ativo=True,
        )
        self.client.force_authenticate(self.user)

    def test_api_criar_sessao_cria_sessao_para_empregado_autenticado(self):
        response = self.client.post(
            reverse("api_dispositivos_criar_sessao"),
            {
                "dispositivo": str(self.dispositivo.pk),
                "furo": str(self.furo.pk),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["empresa"], self.empresa.pk)
        self.assertEqual(response.data["dispositivo"], self.dispositivo.pk)
        self.assertEqual(response.data["furo"], self.furo.pk)

    def test_api_criar_sessao_bloqueia_dispositivo_de_outra_empresa(self):
        empresa_externa = criar_empresa(nome="Empresa API Externa")
        dispositivo_externo = Dispositivo.objects.create(
            empresa=empresa_externa,
            nome="MagCruiser Externo",
            tipo="magcruiser",
            canal="usb_serial",
            porta="/dev/ttyUSB9",
            baudrate=115200,
            ativo=True,
        )

        response = self.client.post(
            reverse("api_dispositivos_criar_sessao"),
            {
                "dispositivo": str(dispositivo_externo.pk),
                "furo": str(self.furo.pk),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("não pertence", response.data["erro"])

    def test_api_bridge_ler_guarda_medicao_em_sessao_ligada(self):
        sessao = criar_sessao_dispositivo(
            dispositivo=self.dispositivo,
            furo=self.furo,
            empregado=self.empregado,
        )
        sessao.status = "ligado"
        sessao.save(update_fields=["status"])

        response = self.client.post(
            reverse("bridge_ler"),
            {
                "sessao_id": str(sessao.pk),
                "payload": "DEPTH=30.00;INC=-6.00;AZI=182.00;MAG=41.20;TEMP=18.50",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ok"])
        self.assertEqual(LeituraBrutaDispositivo.objects.filter(sessao=sessao).count(), 1)
        self.assertEqual(SurveyShot.objects.filter(sessao=sessao, furo=self.furo).count(), 1)
        self.assertEqual(Medicao.objects.filter(furo=self.furo, empresa=self.empresa).count(), 1)

    def test_api_bridge_ler_nao_expoe_sessao_de_outra_empresa(self):
        empresa_externa = criar_empresa(nome="Empresa Bridge Externa")
        projeto_externo = criar_projeto(empresa=empresa_externa, nome="Projeto Bridge Externo")
        furo_externo = criar_furo(
            empresa=empresa_externa,
            projeto=projeto_externo,
            nome="Furo Bridge Externo",
        )
        empregado_externo = criar_empregado(empresa=empresa_externa, nome="Empregado Bridge Externo")
        dispositivo_externo = Dispositivo.objects.create(
            empresa=empresa_externa,
            nome="MagCruiser Bridge Externo",
            tipo="magcruiser",
            canal="usb_serial",
            porta="/dev/ttyUSB8",
            baudrate=115200,
            ativo=True,
        )
        sessao_externa = criar_sessao_dispositivo(
            dispositivo=dispositivo_externo,
            furo=furo_externo,
            empregado=empregado_externo,
        )
        sessao_externa.status = "ligado"
        sessao_externa.save(update_fields=["status"])

        response = self.client.post(
            reverse("bridge_ler"),
            {
                "sessao_id": str(sessao_externa.pk),
                "payload": "DEPTH=31.00;INC=-7.00;AZI=183.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(LeituraBrutaDispositivo.objects.filter(sessao=sessao_externa).count(), 0)

    def test_api_bridge_ler_payload_invalido_devolve_erro_controlado(self):
        sessao = criar_sessao_dispositivo(
            dispositivo=self.dispositivo,
            furo=self.furo,
            empregado=self.empregado,
        )
        sessao.status = "ligado"
        sessao.save(update_fields=["status"])

        response = self.client.post(
            reverse("bridge_ler"),
            {
                "sessao_id": str(sessao.pk),
                "payload": "ruido_sem_campos_obrigatorios",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["ok"])
        self.assertIn("erro", response.data)
        self.assertEqual(LeituraBrutaDispositivo.objects.filter(sessao=sessao).count(), 0)


class DispositivoAdminApiEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.empresa = criar_empresa(nome="Empresa Admin API Dispositivos")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Admin API Dispositivos")
        self.furo = criar_furo(
            empresa=self.empresa,
            projeto=self.projeto,
            nome="Furo Admin API Dispositivos",
        )
        self.user = criar_user(username="superuser_dispositivos")
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save(update_fields=["is_superuser", "is_staff"])
        self.client.force_login(self.user)

    def test_api_guardar_dispositivo_detectado_rejeita_baudrate_invalido(self):
        response = self.client.post(
            reverse("dispositivos:api_guardar_dispositivo_detectado"),
            {
                "canal": "usb_serial",
                "name": "MagCruiser Baudrate Inválido",
                "identifier": "/dev/ttyUSB9",
                "baudrate": "abc",
                "furo_id": str(self.furo.pk),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.assertIn("Baudrate inválido", response.json()["eventos"][0]["mensagem"])
        self.assertFalse(Dispositivo.objects.filter(empresa=self.empresa, porta="/dev/ttyUSB9").exists())

    def test_api_guardar_dispositivo_detectado_usa_baudrate_padrao_quando_vazio(self):
        response = self.client.post(
            reverse("dispositivos:api_guardar_dispositivo_detectado"),
            {
                "canal": "usb_serial",
                "name": "MagCruiser Baudrate Padrão",
                "identifier": "/dev/ttyUSB7",
                "baudrate": "",
                "furo_id": str(self.furo.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        dispositivo = Dispositivo.objects.get(empresa=self.empresa, porta="/dev/ttyUSB7")
        self.assertEqual(dispositivo.baudrate, 115200)
