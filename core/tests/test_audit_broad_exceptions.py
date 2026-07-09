from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase


class AuditBroadExceptionsCommandTests(SimpleTestCase):
    def test_reporta_except_exception_sem_falhar_por_defeito(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.py"
            path.write_text(
                "try:\n"
                "    risky()\n"
                "except Exception:\n"
                "    pass\n",
                encoding="utf-8",
            )
            stdout = StringIO()

            call_command("audit_broad_exceptions", "--path", tmpdir, stdout=stdout)

            output = stdout.getvalue()
            self.assertIn("sample.py:3", output)
            self.assertIn("Exception", output)
            self.assertIn("1 ocorrência", output)

    def test_fail_on_found_falha_quando_ha_handler_generico(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.py"
            path.write_text(
                "try:\n"
                "    risky()\n"
                "except:\n"
                "    pass\n",
                encoding="utf-8",
            )
            stdout = StringIO()

            with self.assertRaises(CommandError):
                call_command("audit_broad_exceptions", "--path", tmpdir, "--fail-on-found", stdout=stdout)

            self.assertIn("bare-except", stdout.getvalue())

    def test_ignora_migrations(self):
        with TemporaryDirectory() as tmpdir:
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()
            (migrations_dir / "0001_initial.py").write_text(
                "try:\n"
                "    risky()\n"
                "except Exception:\n"
                "    pass\n",
                encoding="utf-8",
            )
            stdout = StringIO()

            call_command("audit_broad_exceptions", "--path", tmpdir, "--fail-on-found", stdout=stdout)

            self.assertIn("0 ocorrência", stdout.getvalue())
