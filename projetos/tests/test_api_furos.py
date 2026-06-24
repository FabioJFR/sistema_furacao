from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from projetos.api.views import FuroListAPIView, FuroVersaoListAPIView
from projetos.tests.helpers import criar_empregado, criar_empresa, criar_user


class FuroApiLimitTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(is_authenticated=True)
        self.empresa = SimpleNamespace(pk="empresa-api")
        self.furo = SimpleNamespace(pk="furo-api")

    def _autenticar(self, request):
        force_authenticate(request, user=self.user)
        return request

    def test_lista_furos_rejeita_limit_nao_inteiro(self):
        request = self._autenticar(self.factory.get("/api/v1/projetos/furos/", {"limit": "abc"}))

        with patch("projetos.api.views._resolver_empresa_api", return_value=(self.empresa, None)):
            response = FuroListAPIView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {"erro": "Parâmetro 'limit' inválido. Usa um número inteiro."},
        )

    def test_lista_versoes_rejeita_limit_nao_inteiro(self):
        request = self._autenticar(
            self.factory.get(
                "/api/v1/projetos/furos/furo-api/versoes/",
                {"limit": "abc"},
            )
        )

        with (
            patch("projetos.api.views._resolver_empresa_api", return_value=(self.empresa, None)),
            patch("projetos.api.views.obter_furo_api", return_value=self.furo),
        ):
            response = FuroVersaoListAPIView.as_view()(request, pk=self.furo.pk)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {"erro": "Parâmetro 'limit' inválido. Usa um número inteiro."},
        )


class FuroApiPermissoesTests(TestCase):
    def test_empregado_pendente_nao_acede_a_furos_da_empresa(self):
        empresa = criar_empresa(nome="Empresa API Empregado Pendente")
        user = criar_user(username="empregado_api_pendente")
        criar_empregado(
            empresa=empresa,
            user=user,
            nome="Empregado API Pendente",
            aprovado=False,
        )
        client = APIClient()
        client.force_authenticate(user)

        response = client.get(reverse("api_v1_furos_list"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["erro"],
            "Conta sem empresa associada para acesso API.",
        )
