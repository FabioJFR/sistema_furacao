# plataforma/forms/plano.py

from django import forms
from plataforma.models import Plano


class PlanoForm(forms.ModelForm):
    class Meta:
        model = Plano
        fields = [
            "nome",
            "descricao",
            "tipo",
            "preco_mensal",
            "preco_anual",
            "limite_empregados",
            "limite_projetos",
            "limite_furos",
            "limite_armazenamento_gb",
            "permite_multiplos_utilizadores",
            "acesso_dashboard_empresa",
            "acesso_painel_empregado",
            "ativo",
        ]

        widgets = {
            "nome": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "descricao": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 3}),
            "tipo": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),

            "preco_mensal": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "preco_anual": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),

            "limite_empregados": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "limite_projetos": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "limite_furos": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "limite_armazenamento_gb": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),

            "permite_multiplos_utilizadores": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "acesso_dashboard_empresa": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "acesso_painel_empregado": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "ativo": forms.CheckboxInput(attrs={"class": "mr-2"}),
        }

    # ---------------- VALIDAÇÕES ----------------

    def clean_preco_mensal(self):
        valor = self.cleaned_data.get("preco_mensal")
        if valor is not None and valor < 0:
            raise forms.ValidationError("O preço mensal não pode ser negativo.")
        return valor

    def clean_preco_anual(self):
        valor = self.cleaned_data.get("preco_anual")
        if valor is not None and valor < 0:
            raise forms.ValidationError("O preço anual não pode ser negativo.")
        return valor

    def clean(self):
        cleaned = super().clean()

        tipo = cleaned.get("tipo")
        permite_multiplos = cleaned.get("permite_multiplos_utilizadores")

        # TODO futuro:
        # - validar limites com base no plano (ex: plano individual não pode ter muitos utilizadores)
        # - ligar validações com faturação (ex: impedir downgrade com uso acima do limite)
        # - adicionar validação de coerência entre mensal/anual

        if tipo == "individual" and permite_multiplos:
            raise forms.ValidationError(
                "Planos individuais não devem permitir múltiplos utilizadores."
            )

        return cleaned