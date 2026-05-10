from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from geologia.models.cartografia import FonteCartograficaGeologica
from geologia.models.drone import DroneOperacaoTempoReal
from geologia.models.drone_sf import OperacaoDroneSFTempoReal


class GeologiaModelUrlSecurityTests(SimpleTestCase):
    def test_fonte_tile_rejeita_url_sem_placeholders(self):
        fonte = FonteCartograficaGeologica(
            nome="Tiles teste",
            tipo_servico="tile",
            url_servico="https://tiles.example.com/base/1/2/3.png",
        )
        with self.assertRaises(ValidationError):
            fonte.clean()

    def test_operacao_drone_rejeita_bridge_url_com_query(self):
        operacao = DroneOperacaoTempoReal(
            bridge_ativa=True,
            bridge_base_url="http://127.0.0.1:8787/api?token=123",
        )
        with self.assertRaises(ValidationError):
            operacao.clean()

    def test_operacao_drone_sf_rejeita_live_view_com_credenciais(self):
        operacao = OperacaoDroneSFTempoReal(
            live_view_url="https://user:pass@example.com/live",
        )
        with self.assertRaises(ValidationError):
            operacao.clean()
