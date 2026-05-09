from django import forms
from django.core.validators import validate_email

from projetos.models import (
    AcaoPreventiva,
    AcaoCorretiva,
    AgendamentoRelatorioExecutivo,
    AuditoriaHSE,
    ChecklistHSE,
    Empregados,
    EvidenciaCompliance,
    FechoAcaoCorretiva,
    FornecedorCompra,
    IncidenteSeguranca,
    NotificacaoGestao,
    PedidoCompra,
    PlanoAuditoriaHSE,
    PropostaFornecedorCompra,
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


class FornecedorCompraForm(forms.ModelForm):
    class Meta:
        model = FornecedorCompra
        fields = [
            "nome",
            "contacto_nome",
            "email",
            "telefone",
            "sla_dias_entrega",
            "avaliacao",
            "ativo",
            "observacoes",
        ]
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_avaliacao(self):
        avaliacao = float(self.cleaned_data.get("avaliacao") or 0.0)
        if avaliacao < 0 or avaliacao > 5:
            raise forms.ValidationError("A avaliação deve estar entre 0 e 5.")
        return avaliacao


class PropostaFornecedorCompraForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is None:
            self.fields["fornecedor"].queryset = FornecedorCompra.objects.none()
            return
        self.fields["fornecedor"].queryset = FornecedorCompra.objects.filter(empresa_id=empresa_id, ativo=True).order_by("nome")

    class Meta:
        model = PropostaFornecedorCompra
        fields = [
            "fornecedor",
            "valor_proposto",
            "prazo_entrega_dias",
            "observacoes",
            "selecionada",
        ]
        widgets = {
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


class AuditoriaHSEForm(forms.ModelForm):
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
        model = AuditoriaHSE
        fields = ["titulo", "area", "projeto", "responsavel", "data_auditoria", "status", "resultado", "observacoes"]
        widgets = {
            "data_auditoria": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class PlanoAuditoriaHSEForm(forms.ModelForm):
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
        model = PlanoAuditoriaHSE
        fields = ["titulo", "area", "projeto", "responsavel", "frequencia", "ativo", "proxima_execucao", "observacoes"]
        widgets = {
            "proxima_execucao": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class AcaoCorretivaForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is None:
            self.fields["projeto"].queryset = Projeto.objects.none()
            self.fields["responsavel"].queryset = Empregados.objects.none()
            self.fields["checklist"].queryset = ChecklistHSE.objects.none()
            self.fields["incidente"].queryset = IncidenteSeguranca.objects.none()
            self.fields["auditoria"].queryset = AuditoriaHSE.objects.none()
            return
        self.fields["projeto"].queryset = Projeto.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["responsavel"].queryset = Empregados.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["checklist"].queryset = ChecklistHSE.objects.filter(empresa_id=empresa_id).order_by("-data_check", "titulo")
        self.fields["incidente"].queryset = IncidenteSeguranca.objects.filter(empresa_id=empresa_id).order_by("-data_incidente", "titulo")
        self.fields["auditoria"].queryset = AuditoriaHSE.objects.filter(empresa_id=empresa_id).order_by("-data_auditoria", "titulo")

    class Meta:
        model = AcaoCorretiva
        fields = [
            "titulo",
            "descricao",
            "projeto",
            "responsavel",
            "checklist",
            "incidente",
            "auditoria",
            "prioridade",
            "status",
            "prazo",
            "observacoes",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "prazo": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        novo_estado = cleaned.get("status")
        estado_atual = getattr(self.instance, "status", "")
        if novo_estado == "concluida" and estado_atual != "concluida":
            raise forms.ValidationError("Usa o fecho formal para concluir a ação corretiva.")
        return cleaned


class AcaoPreventivaForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is None:
            self.fields["projeto"].queryset = Projeto.objects.none()
            self.fields["responsavel"].queryset = Empregados.objects.none()
            self.fields["checklist"].queryset = ChecklistHSE.objects.none()
            self.fields["incidente"].queryset = IncidenteSeguranca.objects.none()
            self.fields["auditoria"].queryset = AuditoriaHSE.objects.none()
            return
        self.fields["projeto"].queryset = Projeto.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["responsavel"].queryset = Empregados.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["checklist"].queryset = ChecklistHSE.objects.filter(empresa_id=empresa_id).order_by("-data_check", "titulo")
        self.fields["incidente"].queryset = IncidenteSeguranca.objects.filter(empresa_id=empresa_id).order_by("-data_incidente", "titulo")
        self.fields["auditoria"].queryset = AuditoriaHSE.objects.filter(empresa_id=empresa_id).order_by("-data_auditoria", "titulo")

    class Meta:
        model = AcaoPreventiva
        fields = [
            "titulo",
            "descricao",
            "projeto",
            "responsavel",
            "checklist",
            "incidente",
            "auditoria",
            "prioridade",
            "status",
            "prazo",
            "observacoes",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "prazo": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class EvidenciaComplianceForm(forms.ModelForm):
    class Meta:
        model = EvidenciaCompliance
        fields = ["tipo", "titulo", "ficheiro", "descricao"]
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Ex.: Foto da correção no terreno"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }


class FechoAcaoCorretivaForm(forms.ModelForm):
    class Meta:
        model = FechoAcaoCorretiva
        fields = ["data_fecho", "resumo_execucao", "eficaz", "observacoes"]
        widgets = {
            "data_fecho": forms.DateInput(attrs={"type": "date"}),
            "resumo_execucao": forms.Textarea(attrs={"rows": 4}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
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
    incluir_pdf = forms.BooleanField(required=False, initial=False)

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
        if not cleaned.get("incluir_csv") and not cleaned.get("incluir_xlsx") and not cleaned.get("incluir_pdf"):
            raise forms.ValidationError("Seleciona pelo menos um anexo (CSV, XLSX ou PDF).")
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
            "incluir_pdf",
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
        if not cleaned.get("incluir_csv") and not cleaned.get("incluir_xlsx") and not cleaned.get("incluir_pdf"):
            raise forms.ValidationError("Seleciona pelo menos um anexo (CSV, XLSX ou PDF).")
        return cleaned
