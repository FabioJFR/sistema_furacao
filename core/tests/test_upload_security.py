from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings

from core.upload_security import _scan_with_clamav


class UploadVirusScanTests(SimpleTestCase):
    @override_settings(
        UPLOAD_VIRUS_SCAN_ENABLED=True,
        UPLOAD_VIRUS_SCAN_FAIL_CLOSED=False,
        UPLOAD_VIRUS_SCAN_COMMAND="clamscan",
    )
    @patch("core.upload_security.subprocess.run", side_effect=FileNotFoundError("missing"))
    def test_scanner_indisponivel_pode_ser_aceite_por_configuracao(self, mocked_run):
        upload = SimpleNamespace(
            seek=lambda *args, **kwargs: None,
            read=lambda *args, **kwargs: b"dummy",
        )
        resultado = _scan_with_clamav(field_name="upload", upload_file=upload)
        self.assertEqual(resultado, "scanner_unavailable")

    @override_settings(
        UPLOAD_VIRUS_SCAN_ENABLED=True,
        UPLOAD_VIRUS_SCAN_FAIL_CLOSED=True,
        UPLOAD_VIRUS_SCAN_COMMAND="clamscan",
    )
    @patch("core.upload_security.subprocess.run", side_effect=FileNotFoundError("missing"))
    def test_scanner_indisponivel_bloqueia_quando_fail_closed(self, mocked_run):
        upload = SimpleNamespace(
            seek=lambda *args, **kwargs: None,
            read=lambda *args, **kwargs: b"dummy",
        )
        with self.assertRaises(ValidationError):
            _scan_with_clamav(field_name="upload", upload_file=upload)

    @override_settings(
        UPLOAD_VIRUS_SCAN_ENABLED=True,
        UPLOAD_VIRUS_SCAN_FAIL_CLOSED=True,
        UPLOAD_VIRUS_SCAN_COMMAND="clamscan",
    )
    @patch(
        "core.upload_security.subprocess.run",
        return_value=SimpleNamespace(returncode=1, stdout="FOUND", stderr=""),
    )
    def test_ficheiro_infectado_e_rejeitado(self, mocked_run):
        upload = SimpleNamespace(
            seek=lambda *args, **kwargs: None,
            read=lambda *args, **kwargs: b"dummy",
        )
        with self.assertRaises(ValidationError):
            _scan_with_clamav(field_name="upload", upload_file=upload)
