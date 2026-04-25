from django import forms

from ..models.projeto import Projeto
from ..selectors.forms import existe_projeto_nome_empresa, resolver_empresa_id



def _resolver_empresa_id(empresa):
    return resolver_empresa_id(empresa)



def _normalizar_texto(valor, usar_title=False):
    if not valor:
        return valor

    valor = valor.strip()
    return valor.title() if usar_title else valor



class ProjetoForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa

        empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is not None:
            self.instance.empresa_id = empresa_id

    class Meta:
        model = Projeto
        fields = ["nome", "cliente", "cidade", "pais", "status", "notas"]
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Nome do projeto"}),
            "cliente": forms.TextInput(attrs={"placeholder": "Cliente"}),
            "cidade": forms.TextInput(attrs={"placeholder": "Ex: Aljustrel"}),
            "pais": forms.TextInput(attrs={"placeholder": "Ex: Portugal"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
            "status": forms.Select(),
        }

    def clean_nome(self):
        nome = _normalizar_texto(self.cleaned_data.get("nome"))

        if not nome:
            raise forms.ValidationError("O nome do projeto é obrigatório.")

        if self.empresa:
            if existe_projeto_nome_empresa(
                nome=nome,
                empresa=self.empresa,
                exclude_pk=self.instance.pk if self.instance.pk else None,
            ):
                raise forms.ValidationError("Já existe um projeto com este nome nesta empresa.")

        return nome

    def clean_cliente(self):
        return _normalizar_texto(self.cleaned_data.get("cliente"))

    def clean_cidade(self):
        return _normalizar_texto(self.cleaned_data.get("cidade"), usar_title=True)

    def clean_pais(self):
        return _normalizar_texto(self.cleaned_data.get("pais"), usar_title=True)
