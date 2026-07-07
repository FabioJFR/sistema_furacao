from io import StringIO
import sys
from types import SimpleNamespace

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings
from django.test.utils import ignore_warnings

from core.management.commands.release_readiness_check import Command


STRONG_SECRET = "release-readiness-secret-key-with-enough-length-and-variety-12345"

SAFE_DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "sistema_furacao_prod",
        "USER": "sistema_furacao_app",
        "PASSWORD": "db-password-forte-para-testes",
        "HOST": "127.0.0.1",
        "PORT": "5432",
    }
}


@ignore_warnings(message="Overriding setting DATABASES can lead to unexpected behavior.")
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
        UPLOAD_VIRUS_SCAN_COMMAND=sys.executable,
        DATABASES=SAFE_DATABASES,
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
        UPLOAD_VIRUS_SCAN_COMMAND=sys.executable,
        DATABASES=SAFE_DATABASES,
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
        self.assertIn("[OK] database-credentials", output)
        self.assertIn("[OK] upload-antivirus", output)
        self.assertIn("0 aviso(s), 0 erro(s)", output)

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
        UPLOAD_VIRUS_SCAN_COMMAND="/caminho/inexistente/clamscan",
        DATABASES=SAFE_DATABASES,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": "redis://127.0.0.1:6379/1",
            }
        },
    )
    def test_strict_falha_quando_antivirus_nao_esta_operacional(self):
        stdout = StringIO()

        with self.assertRaises(CommandError):
            call_command(
                "release_readiness_check",
                "--strict",
                "--skip-db",
                "--skip-system-check",
                stdout=stdout,
            )

        output = stdout.getvalue()
        self.assertIn("[ERRO] upload-antivirus", output)
        self.assertIn("executável disponível", output)

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
        UPLOAD_VIRUS_SCAN_COMMAND=sys.executable,
        DATABASES=SAFE_DATABASES,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "tests",
            }
        },
    )
    def test_strict_falha_quando_cache_de_rate_limit_nao_e_partilhada(self):
        stdout = StringIO()

        with self.assertRaises(CommandError):
            call_command(
                "release_readiness_check",
                "--strict",
                "--skip-db",
                "--skip-system-check",
                stdout=stdout,
            )

        output = stdout.getvalue()
        self.assertIn("[ERRO] cache-rate-limit", output)
        self.assertIn("Redis/Memcached", output)

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
        UPLOAD_VIRUS_SCAN_COMMAND=sys.executable,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "postgres_db",
                "USER": "postgres",
                "PASSWORD": "postgres",
                "HOST": "127.0.0.1",
                "PORT": "5432",
            }
        },
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": "redis://127.0.0.1:6379/1",
            }
        },
    )
    def test_strict_falha_com_credenciais_default_de_base_de_dados(self):
        stdout = StringIO()

        with self.assertRaises(CommandError):
            call_command(
                "release_readiness_check",
                "--strict",
                "--skip-db",
                "--skip-system-check",
                stdout=stdout,
            )

        output = stdout.getvalue()
        self.assertIn("[ERRO] database-credentials", output)
        self.assertIn("POSTGRES_DB, POSTGRES_USER e POSTGRES_PASSWORD", output)

    def test_migracao_critica_dispositivos_aplicada_fica_ok(self):
        command = Command()
        loader = SimpleNamespace(
            applied_migrations={
                ("dispositivos", "0006_importacaodispositivohistorico"),
            }
        )

        itens = command._avaliar_migracoes_criticas(loader)

        self.assertEqual(len(itens), 1)
        self.assertTrue(itens[0].ok)
        self.assertEqual(itens[0].slug, "migration:dispositivos.0006_importacaodispositivohistorico")

    def test_migracao_critica_dispositivos_em_falta_fica_erro(self):
        command = Command()
        loader = SimpleNamespace(applied_migrations=set())

        itens = command._avaliar_migracoes_criticas(loader)

        self.assertEqual(len(itens), 1)
        self.assertFalse(itens[0].ok)
        self.assertEqual(itens[0].nivel, "erro")
        self.assertIn("não está aplicada", itens[0].mensagem)
