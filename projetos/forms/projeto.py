from django import forms

from ..models.cliente_contrato import ClienteComercial, ClienteContrato
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
        self.clientes_sugeridos = []

        empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is not None:
            self.instance.empresa_id = empresa_id
            self.clientes_sugeridos = self._carregar_clientes_sugeridos(empresa_id)
            if self.clientes_sugeridos:
                self.fields["cliente"].widget.attrs["list"] = "projeto-cliente-sugestoes"
                self.fields["cliente"].help_text = "Sugestões carregadas dos clientes já registados na empresa."
        self.fields["nome"].help_text = "Para o MVP, basta um nome claro para abrir a frente de trabalho."
        self.fields["cliente"].required = False
        self.fields["cidade"].required = False
        self.fields["pais"].required = False
        self.fields["status"].initial = self.fields["status"].initial or "ativo"
        self.fields["notas"].help_text = "Opcional: contexto útil para a equipa de terreno."

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

    @staticmethod
    def _carregar_clientes_sugeridos(empresa_id):
        nomes = []
        vistos = set()

        for nome in ClienteComercial.objects.filter(empresa_id=empresa_id).values_list("nome_cliente", flat=True):
            nome_normalizado = (nome or "").strip()
            chave = nome_normalizado.casefold()
            if nome_normalizado and chave not in vistos:
                vistos.add(chave)
                nomes.append(nome_normalizado)

        for nome in ClienteContrato.objects.filter(empresa_id=empresa_id).values_list("nome_cliente", flat=True):
            nome_normalizado = (nome or "").strip()
            chave = nome_normalizado.casefold()
            if nome_normalizado and chave not in vistos:
                vistos.add(chave)
                nomes.append(nome_normalizado)

        return sorted(nomes, key=str.casefold)

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
