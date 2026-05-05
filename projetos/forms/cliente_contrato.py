from django import forms

from projetos.models import ClienteContrato, Projeto
from projetos.selectors.forms import resolver_empresa_id


class ClienteContratoForm(forms.ModelForm):
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
            "contacto_nome",
            "contacto_email",
            "contacto_telefone",
            "data_inicio",
            "data_fim",
            "status",
            "notas",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }
