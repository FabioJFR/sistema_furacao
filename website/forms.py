from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class LoginConsentForm(AuthenticationForm):
    confirmar_termos = forms.BooleanField(
        required=True,
        label=_("Li e concordo com os Termos & Condições e com a Política de Privacidade."),
        error_messages={
            "required": _("Tens de confirmar os Termos & Condições e a Política de Privacidade para entrar."),
        },
    )
