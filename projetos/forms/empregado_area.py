from django import forms

from projetos.models import Empregados



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _normalizar_telefone(valor):
    if valor:
        return str(valor).strip()
    return valor



class MeusDadosEmpregadoForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa

    class Meta:
        model = Empregados
        fields = [
            "nome",
            "funcao",
            "email",
            "telefone",
            "data_admissao",
            "idade",
            "morada",
            "nacionalidade",
            "nif",
            "curriculo",
            "contrato",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "funcao": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
            "data_admissao": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "idade": forms.NumberInput(attrs={"class": "form-control"}),
            "morada": forms.TextInput(attrs={"class": "form-control"}),
            "nacionalidade": forms.TextInput(attrs={"class": "form-control"}),
            "nif": forms.NumberInput(attrs={"class": "form-control"}),
            "curriculo": forms.FileInput(attrs={"class": "form-control"}),
            "contrato": forms.FileInput(attrs={"class": "form-control"}),
        }

    def clean_telefone(self):
        return _normalizar_telefone(self.cleaned_data.get("telefone"))

    def clean(self):
        cleaned = super().clean()

        if self.instance and self.instance.pk and self.empresa is not None:
            empresa_id = _resolver_empresa_id(self.empresa)
            if self.instance.empresa_id and self.instance.empresa_id != empresa_id:
                raise forms.ValidationError("Este empregado não pertence à empresa atual.")

        return cleaned