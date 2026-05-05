from django import forms

from projetos.models import AssiduidadeRegisto, Empregados, Projeto
from projetos.selectors.forms import resolver_empresa_id


class AssiduidadeRegistoForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is None:
            self.fields["empregado"].queryset = Empregados.objects.none()
            self.fields["projeto"].queryset = Projeto.objects.none()
            return
        self.instance.empresa_id = empresa_id
        self.fields["empregado"].queryset = Empregados.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["projeto"].queryset = Projeto.objects.filter(empresa_id=empresa_id).order_by("nome")

    class Meta:
        model = AssiduidadeRegisto
        fields = [
            "empregado",
            "projeto",
            "tipo",
            "estado",
            "data_inicio",
            "data_fim",
            "horas",
            "motivo",
            "notas",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }
