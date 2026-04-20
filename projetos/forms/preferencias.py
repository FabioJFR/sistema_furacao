from django import forms
from projetos.models import PreferenciasUser


class PreferenciasForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Garantir associação ao utilizador atual ao criar
        if self.user and not self.instance.pk:
            self.instance.user = self.user

    class Meta:
        model = PreferenciasUser
        fields = ["tema", "idioma"]
        widgets = {
            "tema": forms.Select(attrs={"class": "form-control"}),
            "idioma": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()

        # Segurança: garantir que o form só manipula preferências do utilizador atual.
        if self.user and self.instance and self.instance.user_id:
            if self.instance.user_id != self.user.id:
                raise forms.ValidationError(
                    "Estas preferências não pertencem ao utilizador atual."
                )

        return cleaned