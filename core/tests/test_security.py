from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.security import SensitivePostRateLimitMiddleware


@override_settings(
    LOGIN_URL="/login/",
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS=2,
    LOGIN_RATE_LIMIT_WINDOW_SECONDS=60,
    REGISTO_RATE_LIMIT_MAX_ATTEMPTS=2,
    REGISTO_RATE_LIMIT_WINDOW_SECONDS=60,
    PASSWORD_RESET_RATE_LIMIT_MAX_ATTEMPTS=2,
    PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS=60,
)
class SensitivePostRateLimitMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        cache.clear()

    def test_bloqueia_login_apos_limite(self):
        middleware = SensitivePostRateLimitMiddleware(
            lambda request: HttpResponse("ok")
        )

        request_1 = self.factory.post("/login/", REMOTE_ADDR="10.0.0.1")
        response_1 = middleware(request_1)
        self.assertEqual(response_1.status_code, 200)

        request_2 = self.factory.post("/login/", REMOTE_ADDR="10.0.0.1")
        response_2 = middleware(request_2)
        self.assertEqual(response_2.status_code, 200)

        request_3 = self.factory.post("/login/", REMOTE_ADDR="10.0.0.1")
        response_3 = middleware(request_3)
        self.assertEqual(response_3.status_code, 429)

    def test_login_com_redirect_limpa_contador(self):
        middleware = SensitivePostRateLimitMiddleware(
            lambda request: HttpResponseRedirect("/app/")
        )

        request_1 = self.factory.post("/login/", REMOTE_ADDR="10.0.0.2")
        response_1 = middleware(request_1)
        self.assertEqual(response_1.status_code, 302)

        request_2 = self.factory.post("/login/", REMOTE_ADDR="10.0.0.2")
        response_2 = middleware(request_2)
        self.assertEqual(response_2.status_code, 302)

        request_3 = self.factory.post("/login/", REMOTE_ADDR="10.0.0.2")
        response_3 = middleware(request_3)
        self.assertEqual(response_3.status_code, 302)

    def test_bloqueia_password_reset_apos_limite(self):
        middleware = SensitivePostRateLimitMiddleware(
            lambda request: HttpResponse("ok")
        )

        request_1 = self.factory.post("/password-reset/", REMOTE_ADDR="10.0.0.3")
        response_1 = middleware(request_1)
        self.assertEqual(response_1.status_code, 200)

        request_2 = self.factory.post("/password-reset/", REMOTE_ADDR="10.0.0.3")
        response_2 = middleware(request_2)
        self.assertEqual(response_2.status_code, 200)

        request_3 = self.factory.post("/password-reset/", REMOTE_ADDR="10.0.0.3")
        response_3 = middleware(request_3)
        self.assertEqual(response_3.status_code, 429)

    def test_bloqueia_registo_apos_limite(self):
        middleware = SensitivePostRateLimitMiddleware(
            lambda request: HttpResponse("ok")
        )

        request_1 = self.factory.post("/registo/", REMOTE_ADDR="10.0.0.4")
        response_1 = middleware(request_1)
        self.assertEqual(response_1.status_code, 200)

        request_2 = self.factory.post("/registo/", REMOTE_ADDR="10.0.0.4")
        response_2 = middleware(request_2)
        self.assertEqual(response_2.status_code, 200)

        request_3 = self.factory.post("/registo/", REMOTE_ADDR="10.0.0.4")
        response_3 = middleware(request_3)
        self.assertEqual(response_3.status_code, 429)
