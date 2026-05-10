from urllib.parse import urlsplit

from django.core.exceptions import ValidationError


def validate_configured_url(
    *,
    field_name: str,
    value: str,
    allowed_schemes=("http", "https"),
    allow_query=True,
    allow_fragment=False,
    allow_credentials=False,
    require_tile_placeholders=False,
):
    if not value:
        return

    parsed = urlsplit(str(value).strip())

    if parsed.scheme not in allowed_schemes:
        raise ValidationError(
            {
                field_name: "A URL deve usar um esquema suportado (http ou https)."
            }
        )

    if not parsed.netloc:
        raise ValidationError({field_name: "A URL deve incluir um host válido."})

    if not allow_credentials and (parsed.username or parsed.password):
        raise ValidationError(
            {
                field_name: (
                    "Não uses credenciais embutidas na URL. Configura segredos em campos próprios."
                )
            }
        )

    if not allow_query and parsed.query:
        raise ValidationError(
            {field_name: "Esta URL não deve incluir parâmetros de query."}
        )

    if not allow_fragment and parsed.fragment:
        raise ValidationError({field_name: "Esta URL não deve incluir fragmentos (#...)."})

    if require_tile_placeholders:
        normalized = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        missing = [token for token in ("{z}", "{x}", "{y}") if token not in normalized]
        if missing:
            raise ValidationError(
                {
                    field_name: (
                        "A URL Tile XYZ deve incluir os placeholders {z}, {x} e {y}."
                    )
                }
            )
