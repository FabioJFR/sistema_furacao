from django import forms

from projetos.models import ClienteComercial, ClienteContrato, ClienteContratoAdenda, ClienteContratoAnexo, Projeto
from projetos.selectors.forms import resolver_empresa_id


class ClienteContratoForm(forms.ModelForm):
    observacao_workflow = forms.CharField(
        required=False,
        label="Observação da mudança de workflow",
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Opcional: regista o motivo da alteração do estado comercial.",
    )

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        empresa_id = resolver_empresa_id(empresa) if empresa is not None else None

        if empresa_id is not None:
            self.instance.empresa_id = empresa_id
            self.fields["projeto"].queryset = Projeto.objects.filter(empresa_id=empresa_id).order_by("nome")
        else:
            self.fields["projeto"].queryset = Projeto.objects.none()

    class Meta:
        model = ClienteContrato
        fields = [
            "nome_cliente",
            "numero_contrato",
            "projeto",
            "tipo_cobranca",
            "valor_contratado",
            "moeda",
            "sla_resposta_horas",
            "renovacao_automatica",
            "periodo_renovacao_meses",
            "dias_alerta_vencimento",
            "workflow_comercial",
            "contacto_nome",
            "contacto_email",
            "contacto_telefone",
            "ultimo_contacto_em",
            "proximo_followup_em",
            "dias_alerta_sem_contacto",
            "data_inicio",
            "data_fim",
            "status",
            "notas",
        ]
        widgets = {
            "ultimo_contacto_em": forms.DateInput(attrs={"type": "date"}),
            "proximo_followup_em": forms.DateInput(attrs={"type": "date"}),
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }


class ClienteContratoAnexoForm(forms.ModelForm):
    class Meta:
        model = ClienteContratoAnexo
        fields = ["titulo", "ficheiro", "descricao"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }


class ClienteContratoAdendaForm(forms.ModelForm):
    class Meta:
        model = ClienteContratoAdenda
        fields = ["titulo", "descricao", "data_adenda", "data_fim_anterior", "valor_adicional", "nova_data_fim", "ficheiro"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "data_adenda": forms.DateInput(attrs={"type": "date"}),
            "data_fim_anterior": forms.DateInput(attrs={"type": "date"}),
            "nova_data_fim": forms.DateInput(attrs={"type": "date"}),
        }


class ClienteComercialForm(forms.ModelForm):
    class Meta:
        model = ClienteComercial
        fields = [
            "contacto_principal_nome",
            "contacto_principal_email",
            "contacto_principal_telefone",
            "contacto_secundario_nome",
            "contacto_secundario_email",
            "contacto_secundario_telefone",
            "classificacao_comercial",
            "notas_comerciais",
        ]
        widgets = {
            "notas_comerciais": forms.Textarea(attrs={"rows": 5}),
        }
