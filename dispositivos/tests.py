from decimal import Decimal
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from dispositivos.drivers.magcruiser.parser import parse_magcruiser_payload
from dispositivos.services.api_flow import construir_resposta_operacao_api
from dispositivos.services.magcruiser_import import parse_magcruiser_file
from dispositivos.services.sessao import (
    _validar_dispositivo_empresa,
    _validar_empregado_empresa,
    _validar_furo_empresa,
)


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
