from django.utils.translation import gettext_lazy as _


PUBLIC_LANGUAGE_OPTIONS = (
    ("pt-pt", _("Português")),
    ("en", _("English")),
)


def public_i18n(request):
    return {
        "public_language_options": [
            {"code": code, "label": label}
            for code, label in PUBLIC_LANGUAGE_OPTIONS
        ]
    }
