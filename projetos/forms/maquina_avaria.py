from django import forms

from projetos.models import Empregados, MaquinaAvaria
from projetos.selectors.maquina_avarias import listar_furos_empresa, listar_maquinas_empresa


class MaquinaAvariaEmpregadoForm(forms.Form):
    maquina = forms.ModelChoiceField(queryset=None, label="Máquina")
    furo = forms.ModelChoiceField(queryset=None, required=False, label="Furo (opcional)")
    descricao = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label="Descrição da avaria")

    def __init__(self, *args, empresa_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["maquina"].queryset = listar_maquinas_empresa(empresa_id)
        self.fields["furo"].queryset = listar_furos_empresa(empresa_id)


class MaquinaAvariaAdminUpdateForm(forms.ModelForm):
    responsavel_empregado = forms.ModelChoiceField(
        queryset=Empregados.objects.none(),
        required=False,
        label="Empregado responsável",
    )

    class Meta:
        model = MaquinaAvaria
        fields = ["responsavel_empregado", "status", "solucao"]
        widgets = {
            "responsavel_empregado": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "solucao": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, empresa_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa_id:
            self.fields["responsavel_empregado"].queryset = Empregados.objects.filter(
                empresa_id=empresa_id,
                aprovado=True,
            ).order_by("nome")


class MaquinaAvariaEmpregadoUpdateForm(forms.ModelForm):
    class Meta:
        model = MaquinaAvaria
        fields = ["status", "solucao"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-control"}),
            "solucao": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
