from io import StringIO

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings


@override_settings(ALLOWED_HOSTS=["testserver"])
class ReleaseSmokeCommandTests(TestCase):
    def test_smoke_publico_valida_rotas_criticas(self):
        stdout = StringIO()

        call_command("release_smoke_check", "--public-only", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("[OK] homepage", output)
        self.assertIn("[OK] login", output)
        self.assertIn("Resumo smoke:", output)

    def test_smoke_autenticado_valida_login_e_rotas_base(self):
        User.objects.create_superuser(
            username="smoke_super",
            email="smoke@example.com",
            password="testpass123",
        )
        stdout = StringIO()

        call_command(
            "release_smoke_check",
            "--username",
            "smoke_super",
            "--password",
            "testpass123",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[OK] auth-login", output)
        self.assertIn("[OK] redirect-pos-login", output)

    def test_smoke_autenticado_exige_username_e_password(self):
        with self.assertRaises(CommandError):
            call_command("release_smoke_check", "--username", "sem_password", stdout=StringIO())
