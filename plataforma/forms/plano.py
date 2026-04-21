# plataforma/forms/plano.py

from django import forms
from plataforma.models import Plano


class PlanoForm(forms.ModelForm):
    periodos_cobranca_disponiveis = forms.MultipleChoiceField(
        label="Períodos de cobrança disponíveis",
        choices=Plano.PERIODO_COBRANCA_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["periodos_cobranca_disponiveis"].initial = [
                str(valor) for valor in self.instance.periodos_cobranca_disponiveis_normalizados
            ]
        else:
            self.fields["periodos_cobranca_disponiveis"].initial = ["1", "12"]

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
        preco_mensal = cleaned.get("preco_mensal")
        preco_anual = cleaned.get("preco_anual")
        periodos_raw = cleaned.get("periodos_cobranca_disponiveis") or []
        periodos = sorted({int(valor) for valor in periodos_raw})

        # TODO futuro:
        # - validar limites com base no plano (ex: plano individual não pode ter muitos utilizadores)
        # - ligar validações com faturação (ex: impedir downgrade com uso acima do limite)
        # - adicionar validação de coerência entre mensal/anual

        if tipo == "individual" and permite_multiplos:
            raise forms.ValidationError(
                "Planos individuais não devem permitir múltiplos utilizadores."
            )

        if not periodos:
            raise forms.ValidationError(
                "O plano deve permitir pelo menos um período de cobrança."
            )

        if any(periodo in [1, 3, 6] for periodo in periodos) and (preco_mensal is None or preco_mensal <= 0):
            self.add_error(
                "preco_mensal",
                "Indique um preço mensal válido para planos com cobrança de 1, 3 ou 6 meses.",
            )

        if 12 in periodos and (preco_anual is None or preco_anual <= 0) and (preco_mensal is None or preco_mensal <= 0):
            self.add_error(
                "preco_anual",
                "Indique um preço anual válido para planos de 12 meses, ou pelo menos um preço mensal para calcular o valor.",
            )

        if tipo == "individual":
            cleaned["limite_empregados"] = 0
            cleaned["limite_projetos"] = 0
            cleaned["permite_multiplos_utilizadores"] = False
            cleaned["acesso_dashboard_empresa"] = False

        cleaned["periodos_cobranca_disponiveis"] = periodos
        cleaned["permite_cobranca_mensal"] = 1 in periodos
        cleaned["permite_cobranca_anual"] = 12 in periodos

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.periodos_cobranca_disponiveis = self.cleaned_data["periodos_cobranca_disponiveis"]
        instance.permite_cobranca_mensal = 1 in instance.periodos_cobranca_disponiveis
        instance.permite_cobranca_anual = 12 in instance.periodos_cobranca_disponiveis
        if commit:
            instance.save()
        return instance
