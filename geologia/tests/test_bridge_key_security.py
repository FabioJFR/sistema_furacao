import json

from django.test import TestCase
from django.urls import reverse

from geologia.models.drone import DroneOperacaoTempoReal
from geologia.models.drone_sf import DroneSF, OperacaoDroneSFTempoReal
from projetos.tests.helpers import criar_empresa


class GeologiaBridgeKeySecurityTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Bridge")
        self.bridge_key = "bridge-key-secreta"
        self.dji_operacao = DroneOperacaoTempoReal.objects.create(
            empresa=self.empresa,
            bridge_ativa=True,
            bridge_api_key=self.bridge_key,
        )
        self.drone_sf = DroneSF.objects.create(
            empresa=self.empresa,
            nome="Drone S_F Bridge",
            status="operacional",
        )
        self.sf_operacao = OperacaoDroneSFTempoReal.objects.create(
            empresa=self.empresa,
            drone=self.drone_sf,
            bridge_ativa=True,
            bridge_base_url="http://127.0.0.1:8890",
            bridge_api_key=self.bridge_key,
        )

    def test_dji_bridge_rejeita_key_em_query_string(self):
        response = self.client.post(
            f"{reverse('geologia:api_bridge_ingest_estado')}?bridge_key={self.bridge_key}",
            data=json.dumps({"estado_bridge": "online"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["ok"])
        self.dji_operacao.refresh_from_db()
        self.assertEqual(self.dji_operacao.estado_conexao, "desligado")
        self.assertEqual(self.dji_operacao.bridge_ultimo_estado, "")

    def test_dji_bridge_rejeita_key_no_body(self):
        response = self.client.post(
            reverse("geologia:api_bridge_ingest_estado"),
            data=json.dumps({"bridge_key": self.bridge_key, "estado_bridge": "online"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["ok"])
        self.dji_operacao.refresh_from_db()
        self.assertEqual(self.dji_operacao.estado_conexao, "desligado")
        self.assertEqual(self.dji_operacao.bridge_ultimo_estado, "")

    def test_dji_bridge_aceita_key_apenas_por_header(self):
        response = self.client.post(
            reverse("geologia:api_bridge_ingest_estado"),
            data=json.dumps({"estado_bridge": "online"}),
            content_type="application/json",
            headers={"X-Bridge-Key": self.bridge_key},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.dji_operacao.refresh_from_db()
        self.assertEqual(self.dji_operacao.estado_conexao, "procurando")
        self.assertEqual(self.dji_operacao.bridge_ultimo_estado, "online")
        self.assertIsNotNone(self.dji_operacao.ultimo_heartbeat)

    def test_drone_sf_bridge_rejeita_key_em_query_string(self):
        response = self.client.post(
            f"{reverse('geologia:api_drone_sf_bridge_ingest_estado')}?bridge_key={self.bridge_key}",
            data=json.dumps({"estado_bridge": "ready"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["ok"])
        self.sf_operacao.refresh_from_db()
        self.assertEqual(self.sf_operacao.estado, "desligado")
        self.assertEqual(self.sf_operacao.bridge_ultimo_estado, "")

    def test_drone_sf_bridge_rejeita_key_no_body(self):
        response = self.client.post(
            reverse("geologia:api_drone_sf_bridge_ingest_estado"),
            data=json.dumps({"bridge_key": self.bridge_key, "estado_bridge": "ready"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["ok"])
        self.sf_operacao.refresh_from_db()
        self.assertEqual(self.sf_operacao.estado, "desligado")
        self.assertEqual(self.sf_operacao.bridge_ultimo_estado, "")

    def test_drone_sf_bridge_aceita_key_apenas_por_header(self):
        response = self.client.post(
            reverse("geologia:api_drone_sf_bridge_ingest_estado"),
            data=json.dumps({"estado_bridge": "ready"}),
            content_type="application/json",
            headers={"X-Bridge-Key": self.bridge_key},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.sf_operacao.refresh_from_db()
        self.assertEqual(self.sf_operacao.estado, "desligado")
        self.assertEqual(self.sf_operacao.bridge_ultimo_estado, "ready")
        self.assertIsNotNone(self.sf_operacao.ultimo_heartbeat)
