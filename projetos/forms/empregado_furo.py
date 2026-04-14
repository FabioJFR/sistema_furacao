from django import forms
from projetos.models import EmpregadoFuro, Empregados


class EmpregadoFuroForm(forms.ModelForm):
    class Meta:
        model = EmpregadoFuro
        fields = [
            "empregado",
            "funcao",
            "data_inicio",
            "data_fim",
            "ativo",
            "observacoes",
        ]
        widgets = {
            "empregado": forms.Select(attrs={"class": "form-control"}),
            "funcao": forms.Select(attrs={"class": "form-control"}),
            "data_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_fim": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["empregado"].queryset = Empregados.objects.order_by("nome")