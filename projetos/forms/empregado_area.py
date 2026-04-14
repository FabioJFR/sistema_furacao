from django import forms
from projetos.models import Empregados


class MeusDadosEmpregadoForm(forms.ModelForm):
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
        valor = self.cleaned_data.get("telefone")
        if valor:
            return str(valor).strip()
        return valor