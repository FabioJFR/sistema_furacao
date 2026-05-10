from django.test import RequestFactory, SimpleTestCase

from geologia.views.logs import _next_url_segura


class NextUrlSeguraTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_aceita_next_relativo(self):
        request = self.factory.post(
            "/app/geologia/logs/1/delete/",
            data={"next": "/app/geologia/meus-logs/"},
            HTTP_HOST="127.0.0.1:8000",
        )
        self.assertEqual(_next_url_segura(request), "/app/geologia/meus-logs/")

    def test_bloqueia_next_absoluto_externo(self):
        request = self.factory.post(
            "/app/geologia/logs/1/delete/",
            data={"next": "https://evil.example/phishing"},
            HTTP_HOST="127.0.0.1:8000",
        )
        self.assertEqual(_next_url_segura(request), "")
