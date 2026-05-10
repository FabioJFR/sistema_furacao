from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from core.url_security import validate_configured_url


class ValidateConfiguredUrlTests(SimpleTestCase):
    def test_rejeita_credenciais_embutidas(self):
        with self.assertRaises(ValidationError):
            validate_configured_url(
                field_name="url",
                value="https://user:pass@example.com/service",
            )

    def test_rejeita_esquema_inesperado(self):
        with self.assertRaises(ValidationError):
            validate_configured_url(
                field_name="url",
                value="ftp://example.com/resource",
            )

    def test_tile_exige_placeholders_xyz(self):
        with self.assertRaises(ValidationError):
            validate_configured_url(
                field_name="url",
                value="https://tiles.example.com/layer/10/20/30.png",
                require_tile_placeholders=True,
            )

    def test_aceita_url_tile_com_placeholders(self):
        validate_configured_url(
            field_name="url",
            value="https://tiles.example.com/layer/{z}/{x}/{y}.png",
            require_tile_placeholders=True,
        )
