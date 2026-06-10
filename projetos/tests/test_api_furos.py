from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from projetos.api.views import FuroListAPIView, FuroVersaoListAPIView


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
