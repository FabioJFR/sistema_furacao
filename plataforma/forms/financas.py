from django import forms
from django.utils import timezone

from plataforma.models import MovimentoFinanceiroPlataforma


class BaseMovimentoFinanceiroForm(forms.ModelForm):
    class Meta:
        model = MovimentoFinanceiroPlataforma
        fields = [
            "categoria",
            "metodo_pagamento",
            "valor_bruto",
            "valor_desconto",
            "valor_imposto",
            "moeda",
            "descricao",
            "numero_documento",
            "entidade_nome",
            "referencia",
            "data_competencia",
            "data_vencimento",
            "data_pagamento",
            "estado",
            "observacoes",
        ]
        widgets = {
            "categoria": forms.Select(attrs={"class": "finance-field"}),
            "metodo_pagamento": forms.Select(attrs={"class": "finance-field"}),
            "valor_bruto": forms.NumberInput(attrs={"class": "finance-field", "step": "0.01", "min": "0"}),
            "valor_desconto": forms.NumberInput(attrs={"class": "finance-field", "step": "0.01", "min": "0"}),
            "valor_imposto": forms.NumberInput(attrs={"class": "finance-field", "step": "0.01", "min": "0"}),
            "moeda": forms.TextInput(attrs={"class": "finance-field"}),
            "descricao": forms.TextInput(attrs={"class": "finance-field"}),
            "numero_documento": forms.TextInput(attrs={"class": "finance-field"}),
            "entidade_nome": forms.TextInput(attrs={"class": "finance-field"}),
            "referencia": forms.TextInput(attrs={"class": "finance-field"}),
            "data_competencia": forms.DateInput(attrs={"class": "finance-field", "type": "date"}),
            "data_vencimento": forms.DateInput(attrs={"class": "finance-field", "type": "date"}),
            "data_pagamento": forms.DateInput(attrs={"class": "finance-field", "type": "date"}),
            "estado": forms.Select(attrs={"class": "finance-field"}),
            "observacoes": forms.Textarea(attrs={"class": "finance-field", "rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        valor_bruto = cleaned.get("valor_bruto") or 0
        valor_desconto = cleaned.get("valor_desconto") or 0
        valor_imposto = cleaned.get("valor_imposto") or 0
        valor_liquido = valor_bruto - valor_desconto + valor_imposto

        if valor_liquido < 0:
            self.add_error("valor_desconto", "O desconto não pode tornar o valor líquido negativo.")

        cleaned["valor"] = valor_liquido
        cleaned["valor_liquido"] = valor_liquido

        if not cleaned.get("data_competencia"):
            cleaned["data_competencia"] = timezone.now().date()

        return cleaned


class EntradaValorForm(BaseMovimentoFinanceiroForm):
    CATEGORIAS = [
        ("subscricao", "Subscrição"),
        ("renovacao", "Renovação"),
        ("pagamento_inicial", "Pagamento inicial"),
        ("ajuste", "Ajuste"),
        ("outro", "Outro"),
    ]

    categoria = forms.ChoiceField(choices=CATEGORIAS, widget=forms.Select(attrs={"class": "finance-field"}))

    def save(self, commit=True):
        movimento = super().save(commit=False)
        movimento.tipo_movimento = "cobranca"
        movimento.natureza_fluxo = "entrada"
        movimento.ciclo_cobranca = movimento.ciclo_cobranca or "unico"
        movimento.valor = self.cleaned_data["valor"]
        movimento.valor_liquido = self.cleaned_data["valor_liquido"]
        if commit:
            movimento.save()
        return movimento


class SaidaValorForm(BaseMovimentoFinanceiroForm):
    CATEGORIAS = [
        ("despesa_servidor", "Servidor / alojamento"),
        ("despesa_publicidade_youtube", "Publicidade YouTube"),
        ("despesa_publicidade_facebook", "Publicidade Facebook"),
        ("despesa_publicidade_tiktok", "Publicidade TikTok"),
        ("despesa_dominio", "Domínio / endereço"),
        ("despesa_ssl_https", "SSL / HTTPS"),
        ("despesa_marketing", "Marketing"),
        ("despesa_software", "Software / ferramentas"),
        ("despesa_operacional", "Despesa operacional"),
        ("outro", "Outro"),
    ]

    categoria = forms.ChoiceField(choices=CATEGORIAS, widget=forms.Select(attrs={"class": "finance-field"}))

    def save(self, commit=True):
        movimento = super().save(commit=False)
        movimento.tipo_movimento = "despesa"
        movimento.natureza_fluxo = "saida"
        movimento.ciclo_cobranca = "unico"
        movimento.valor = self.cleaned_data["valor"]
        movimento.valor_liquido = self.cleaned_data["valor_liquido"]
        if commit:
            movimento.save()
        return movimento
