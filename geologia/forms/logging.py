from django import forms

from projetos.models import Medicao
from geologia.models import LogGeologicoFuro


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


class LogGeologicoFuroForm(forms.ModelForm):
    def __init__(self, *args, furo=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.furo = furo
        self.empresa = empresa

        if self.furo is not None:
            self.instance.furo = self.furo
        if self.empresa is not None:
            self.instance.empresa_id = _resolver_empresa_id(self.empresa)

        if self.furo is not None:
            medicoes_qs = Medicao.objects.filter(furo=self.furo).order_by("-criado_em", "-profundidade_medida")
            self.fields["medicao"].queryset = medicoes_qs
            self.fields["missao_drone"].queryset = self.furo.missoes_drone_geologia.all().order_by("-data_voo", "-criado_em")

    class Meta:
        model = LogGeologicoFuro
        fields = [
            "titulo",
            "data_registo",
            "intervalo_de",
            "intervalo_ate",
            "medicao",
            "missao_drone",
            "recuperacao_testemunho_percent",
            "rqd_percent",
            "litologia_principal",
            "litologia_secundaria",
            "cor",
            "granulometria",
            "alteracao",
            "mineralizacao",
            "estrutura",
            "densidade_fraturas",
            "nivel_agua_m",
            "imagem_referencia",
            "observacoes",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "data_registo": forms.DateInput(attrs={"class": "border rounded px-3 py-2 w-full", "type": "date"}),
            "intervalo_de": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "intervalo_ate": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "medicao": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "missao_drone": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "recuperacao_testemunho_percent": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "rqd_percent": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "litologia_principal": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "litologia_secundaria": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "cor": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "granulometria": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "alteracao": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "mineralizacao": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "estrutura": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "densidade_fraturas": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "nivel_agua_m": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "imagem_referencia": forms.FileInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "observacoes": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        if self.furo and self.empresa is not None:
            empresa_id = _resolver_empresa_id(self.empresa)
            if self.furo.empresa_id != empresa_id:
                raise forms.ValidationError("O furo selecionado nao pertence a empresa atual.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.furo is not None:
            instance.furo = self.furo
        if self.empresa is not None:
            instance.empresa_id = _resolver_empresa_id(self.empresa)
        if commit:
            instance.save()
        return instance

