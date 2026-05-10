from django import forms
from plataforma.models import Empresa
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
        fields = [
            "tema",
            "paleta",
            "idioma",
            "tamanho_texto",
            "ajuda_contextual_ativa",
            "ajuda_contextual_apenas_paginas_novas",
            "ajuda_contextual_apenas_utilizadores_recentes",
        ]
        widgets = {
            "tema": forms.Select(attrs={"class": "form-control"}),
            "paleta": forms.Select(attrs={"class": "form-control"}),
            "idioma": forms.Select(attrs={"class": "form-control"}),
            "tamanho_texto": forms.Select(attrs={"class": "form-control"}),
            "ajuda_contextual_ativa": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-gray-300 text-cyan-600 focus:ring-cyan-500"}),
            "ajuda_contextual_apenas_paginas_novas": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-gray-300 text-cyan-600 focus:ring-cyan-500"}),
            "ajuda_contextual_apenas_utilizadores_recentes": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-gray-300 text-cyan-600 focus:ring-cyan-500"}),
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


class EmpresaFinanceiraForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ["custo_por_metro_cliente", "outros_valores_gastos_associados"]
        widgets = {
            "custo_por_metro_cliente": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "outros_valores_gastos_associados": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
        }

    def clean_custo_por_metro_cliente(self):
        valor = self.cleaned_data.get("custo_por_metro_cliente") or 0
        if valor < 0:
            raise forms.ValidationError("O custo por metro do cliente não pode ser negativo.")
        return valor

    def clean_outros_valores_gastos_associados(self):
        valor = self.cleaned_data.get("outros_valores_gastos_associados") or 0
        if valor < 0:
            raise forms.ValidationError("Os outros valores gastos associados não podem ser negativos.")
        return valor
