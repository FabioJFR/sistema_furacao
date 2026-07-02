from io import StringIO

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings


STRONG_SECRET = "release-readiness-secret-key-with-enough-length-and-variety-12345"


class ReleaseReadinessCommandTests(SimpleTestCase):
    @override_settings(
        DEBUG=True,
        SECRET_KEY=STRONG_SECRET,
        ALLOWED_HOSTS=[],
        SESSION_COOKIE_SECURE=False,
        CSRF_COOKIE_SECURE=False,
        SECURE_SSL_REDIRECT=False,
        SECURE_HSTS_SECONDS=0,
        UPLOAD_VIRUS_SCAN_ENABLED=False,
        UPLOAD_VIRUS_SCAN_FAIL_CLOSED=False,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "tests",
            }
        },
    )
    def test_modo_pre_demo_reporta_avisos_sem_falhar(self):
        stdout = StringIO()

        call_command(
            "release_readiness_check",
            "--skip-db",
            "--skip-system-check",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[AVISO] debug", output)
        self.assertIn("Resumo:", output)

    @override_settings(
        DEBUG=True,
        SECRET_KEY="weak",
        ALLOWED_HOSTS=["localhost"],
        SESSION_COOKIE_SECURE=False,
        CSRF_COOKIE_SECURE=False,
        SECURE_SSL_REDIRECT=False,
        SECURE_HSTS_SECONDS=0,
        UPLOAD_VIRUS_SCAN_ENABLED=False,
        UPLOAD_VIRUS_SCAN_FAIL_CLOSED=False,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "tests",
            }
        },
    )
    def test_modo_pre_demo_nao_falha_com_secret_key_fraca_local(self):
        stdout = StringIO()

        call_command(
            "release_readiness_check",
            "--skip-db",
            "--skip-system-check",
            stdout=stdout,
        )

        self.assertIn("[AVISO] secret-key", stdout.getvalue())

    @override_settings(
        DEBUG=True,
        SECRET_KEY=STRONG_SECRET,
        ALLOWED_HOSTS=["sistemafuracao.pt"],
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_SSL_REDIRECT=True,
        SECURE_HSTS_SECONDS=31536000,
        UPLOAD_VIRUS_SCAN_ENABLED=True,
        UPLOAD_VIRUS_SCAN_FAIL_CLOSED=True,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": "redis://127.0.0.1:6379/1",
            }
        },
    )
    def test_strict_falha_quando_debug_ativo(self):
        stdout = StringIO()

        with self.assertRaises(CommandError):
            call_command(
                "release_readiness_check",
                "--strict",
                "--skip-db",
                "--skip-system-check",
                stdout=stdout,
            )

        self.assertIn("[ERRO] debug", stdout.getvalue())

    @override_settings(
        DEBUG=False,
        SECRET_KEY=STRONG_SECRET,
        ALLOWED_HOSTS=["sistemafuracao.pt"],
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_SSL_REDIRECT=True,
        SECURE_HSTS_SECONDS=31536000,
        UPLOAD_VIRUS_SCAN_ENABLED=True,
        UPLOAD_VIRUS_SCAN_FAIL_CLOSED=True,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": "redis://127.0.0.1:6379/1",
            }
        },
    )
    def test_strict_passa_com_configuracao_producao_simulada(self):
        stdout = StringIO()

        call_command(
            "release_readiness_check",
            "--strict",
            "--skip-db",
            "--skip-system-check",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[OK] debug", output)
        self.assertIn("0 aviso(s), 0 erro(s)", output)
