from django import forms

from plataforma.models import ConfiguracaoPagamentoPlataforma


class ConfiguracaoPaypalForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoPagamentoPlataforma
        fields = [
            "paypal_email",
            "paypal_password",
            "ativo",
        ]
        widgets = {
            "paypal_email": forms.EmailInput(attrs={"class": "finance-field", "placeholder": "email@paypal.com"}),
            "paypal_password": forms.PasswordInput(
                attrs={"class": "finance-field", "placeholder": "Palavra-passe da conta PayPal"},
                render_value=True,
            ),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_paypal_email(self):
        return (self.cleaned_data.get("paypal_email") or "").strip()

    def clean_paypal_password(self):
        return (self.cleaned_data.get("paypal_password") or "").strip()
