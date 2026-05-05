from django import forms
from django.core.validators import validate_email

from projetos.models import (
    AgendamentoRelatorioExecutivo,
    ChecklistHSE,
    Empregados,
    IncidenteSeguranca,
    NotificacaoGestao,
    PedidoCompra,
    Projeto,
)
from projetos.selectors.forms import resolver_empresa_id


class PedidoCompraForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is None:
            self.fields["projeto"].queryset = Projeto.objects.none()
            self.fields["solicitado_por"].queryset = Empregados.objects.none()
            return
        self.fields["projeto"].queryset = Projeto.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["solicitado_por"].queryset = Empregados.objects.filter(empresa_id=empresa_id).order_by("nome")

    class Meta:
        model = PedidoCompra
        fields = [
            "projeto",
            "solicitado_por",
            "descricao",
            "categoria",
            "fornecedor_sugerido",
            "valor_estimado",
            "prioridade",
            "data_necessidade",
            "observacoes",
        ]
        widgets = {
            "data_necessidade": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class NotificacaoGestaoForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is None:
            self.fields["responsavel"].queryset = Empregados.objects.none()
            return
        self.fields["responsavel"].queryset = Empregados.objects.filter(empresa_id=empresa_id).order_by("nome")

    class Meta:
        model = NotificacaoGestao
        fields = ["titulo", "tipo", "prioridade", "estado", "responsavel", "prazo", "origem_url", "detalhes"]
        widgets = {
            "prazo": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "detalhes": forms.Textarea(attrs={"rows": 3}),
        }


class ChecklistHSEForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is None:
            self.fields["projeto"].queryset = Projeto.objects.none()
            self.fields["responsavel"].queryset = Empregados.objects.none()
            return
        self.fields["projeto"].queryset = Projeto.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["responsavel"].queryset = Empregados.objects.filter(empresa_id=empresa_id).order_by("nome")

    class Meta:
        model = ChecklistHSE
        fields = ["titulo", "area", "projeto", "responsavel", "data_check", "status", "observacoes"]
        widgets = {
            "data_check": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class IncidenteSegurancaForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is None:
            self.fields["projeto"].queryset = Projeto.objects.none()
            self.fields["reportado_por"].queryset = Empregados.objects.none()
            self.fields["responsavel"].queryset = Empregados.objects.none()
            return
        base_qs = Empregados.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["projeto"].queryset = Projeto.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["reportado_por"].queryset = base_qs
        self.fields["responsavel"].queryset = base_qs

    class Meta:
        model = IncidenteSeguranca
        fields = [
            "titulo",
            "descricao",
            "projeto",
            "reportado_por",
            "responsavel",
            "gravidade",
            "status",
            "data_incidente",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "data_incidente": forms.DateInput(attrs={"type": "date"}),
        }


class RelatorioExecutivoEmailForm(forms.Form):
    assunto = forms.CharField(max_length=200, required=False)
    destinos = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "email1@dominio.pt, email2@dominio.pt"}),
        help_text="Se vazio, usa automaticamente o email da empresa/responsável.",
    )
    incluir_csv = forms.BooleanField(required=False, initial=True)
    incluir_xlsx = forms.BooleanField(required=False, initial=True)

    def clean_destinos(self):
        raw = (self.cleaned_data.get("destinos") or "").strip()
        if not raw:
            self.cleaned_data["destinos_lista"] = []
            return raw

        separadores = [",", ";", "\n", "\r", "\t"]
        for separador in separadores:
            raw = raw.replace(separador, " ")

        candidatos = [item.strip() for item in raw.split(" ") if item.strip()]
        destinos_lista = []
        for email in candidatos:
            validate_email(email)
            destinos_lista.append(email.lower())

        unicos = list(dict.fromkeys(destinos_lista))
        self.cleaned_data["destinos_lista"] = unicos
        return ", ".join(unicos)

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("incluir_csv") and not cleaned.get("incluir_xlsx"):
            raise forms.ValidationError("Seleciona pelo menos um anexo (CSV ou XLSX).")
        return cleaned


class AgendamentoRelatorioExecutivoForm(forms.ModelForm):
    class Meta:
        model = AgendamentoRelatorioExecutivo
        fields = [
            "ativo",
            "frequencia",
            "hora_execucao",
            "dia_semana",
            "dia_mes",
            "destinos",
            "incluir_csv",
            "incluir_xlsx",
        ]
        widgets = {
            "hora_execucao": forms.TimeInput(attrs={"type": "time"}),
            "destinos": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_dia_semana(self):
        valor = int(self.cleaned_data.get("dia_semana") or 0)
        if valor < 0 or valor > 6:
            raise forms.ValidationError("O dia da semana deve estar entre 0 (segunda) e 6 (domingo).")
        return valor

    def clean_dia_mes(self):
        valor = int(self.cleaned_data.get("dia_mes") or 1)
        if valor < 1 or valor > 28:
            raise forms.ValidationError("O dia do mês deve estar entre 1 e 28.")
        return valor

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("incluir_csv") and not cleaned.get("incluir_xlsx"):
            raise forms.ValidationError("Seleciona pelo menos um anexo (CSV ou XLSX).")
        return cleaned
