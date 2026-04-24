import json

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from ..models.individual import Individual
from ..models.empregado import Empregados, EmpregadoFicheiro, EmpregadoProjeto
from ..selectors.forms import (
    existe_empregado_por_email,
    existe_user_por_email,
    existe_user_por_username,
    listar_empregados_empresa_qs,
    listar_empresas_por_nome,
    listar_furos_empresa_qs,
    listar_projetos_empresa_qs,
    listar_users_disponiveis_para_empregado,
    resolver_empresa_id,
)



def _resolver_empresa_id(empresa):
    return resolver_empresa_id(empresa)



def _normalizar_telefone(valor):
    if valor:
        return str(valor).strip()
    return valor



def _validar_furos_empresa(form, furos, empresa=None):
    if empresa is None or not furos:
        return

    empresa_id = _resolver_empresa_id(empresa)
    for furo in furos:
        if furo.empresa_id != empresa_id:
            form.add_error("furos", "Um dos furos selecionados não pertence à empresa atual.")
            break



def _clean_json_field(data, field_name):
    if not data:
        return []

    try:
        valor = json.loads(data)
    except json.JSONDecodeError:
        raise forms.ValidationError(f"JSON inválido para {field_name}")

    return valor



def _obter_queryset_furos_empresa(empresa=None):
    return listar_furos_empresa_qs(empresa)



def _obter_queryset_projetos_empresa(empresa=None):
    return listar_projetos_empresa_qs(empresa)



def _atribuir_empresa_instance(instance, empresa=None):
    if empresa is not None:
        instance.empresa_id = _resolver_empresa_id(empresa)
    return instance


# ---------------- Empregados ----------------

class EmpregadoRegistroForm(UserCreationForm):
    TIPO_CONTA_CHOICES = [
        ("empregado", "Pertence a uma empresa"),
        ("individual", "Conta individual"),
    ]

    tipo_conta = forms.ChoiceField(
        label="Tipo de conta",
        choices=TIPO_CONTA_CHOICES,
        initial="empregado",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    empresa_nome = forms.CharField(
        label="Nome da empresa",
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="Introduza exatamente o nome da empresa que te foi indicado.",
        required=False,
    )
    username = forms.CharField(
        label="Nome de utilizador",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    nome = forms.CharField(
        label="Nome completo",
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    telefone = forms.CharField(
        label="Telefone",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    funcao = forms.ChoiceField(
        label="Função",
        required=False,
        choices=Empregados._meta.get_field("funcao").choices,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    especialidade = forms.CharField(
        label="Especialidade",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="Opcional para contas individuais.",
    )
    password1 = forms.CharField(
        label="Palavra-passe",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="A palavra-passe deve ter pelo menos 8 caracteres e não deve ser parecida com o nome de utilizador.",
    )
    password2 = forms.CharField(
        label="Confirmar palavra-passe",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="Introduza novamente a mesma palavra-passe.",
    )

    class Meta:
        model = User
        fields = [
            "tipo_conta",
            "empresa_nome",
            "username",
            "nome",
            "email",
            "telefone",
            "funcao",
            "especialidade",
            "password1",
            "password2",
        ]

    def clean_empresa_nome(self):
        tipo_conta = self.cleaned_data.get("tipo_conta")
        valor = self.cleaned_data.get("empresa_nome", "").strip()
        if tipo_conta != "empregado":
            self.empresa_resolvida = None
            return valor
        if len(valor) < 2:
            raise forms.ValidationError("Indica o nome da empresa.")

        empresas = listar_empresas_por_nome(valor)

        if not empresas.exists():
            raise forms.ValidationError(
                "Não foi encontrada nenhuma empresa com esse nome. Confirma o nome exato com a tua empresa."
            )

        if empresas.count() > 1:
            raise forms.ValidationError(
                "Existem várias empresas com esse nome. Pede à empresa o nome exato que deves usar."
            )

        self.empresa_resolvida = empresas.first()
        return valor

    def clean(self):
        cleaned = super().clean()
        tipo_conta = cleaned.get("tipo_conta")
        if tipo_conta == "empregado" and not cleaned.get("empresa_nome"):
            self.add_error("empresa_nome", "Indica o nome da empresa.")
        if tipo_conta == "individual":
            cleaned["funcao"] = ""
        return cleaned

    def clean_nome(self):
        valor = self.cleaned_data.get("nome", "").strip()
        if len(valor) < 3:
            raise forms.ValidationError("O nome deve ter pelo menos 3 caracteres.")
        return valor

    def clean_telefone(self):
        return _normalizar_telefone(self.cleaned_data.get("telefone"))

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if existe_user_por_email(email):
            raise forms.ValidationError("Já existe uma conta com este email.")
        return email


class BaseEmpregadoForm(forms.ModelForm):
    alertas = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        required=False,
        help_text="Lista JSON de alertas",
    )

    def clean_telefone(self):
        return _normalizar_telefone(self.cleaned_data.get("telefone"))

    def clean_alertas(self):
        data = self.cleaned_data.get("alertas", "[]")
        valor = _clean_json_field(data, "alertas")

        if valor and not isinstance(valor, list):
            raise forms.ValidationError("O campo alertas deve conter uma lista JSON.")

        return valor

    def _configurar_empresa(self, empresa=None):
        self.empresa = empresa
        _atribuir_empresa_instance(self.instance, empresa=self.empresa)

        if "empresa" in self.fields:
            self.fields["empresa"].widget = forms.HiddenInput()
            self.fields["empresa"].required = False

        if "furos" in self.fields:
            self.fields["furos"].queryset = _obter_queryset_furos_empresa(self.empresa)

    def _validar_empresa_instancia(self, mensagem):
        if self.instance and self.instance.pk and self.empresa is not None:
            empresa_id = _resolver_empresa_id(self.empresa)
            if self.instance.empresa_id and self.instance.empresa_id != empresa_id:
                raise forms.ValidationError(mensagem)

    def _validar_furos_empresa_clean(self, cleaned):
        _validar_furos_empresa(self, cleaned.get("furos"), empresa=self.empresa)


class EmpregadosForm(BaseEmpregadoForm):
    class Meta:
        model = Empregados
        fields = "__all__"
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "funcao": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "data_admissao": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_inicio_contrato": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_fim_contrato": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
            "idade": forms.NumberInput(attrs={"class": "form-control"}),
            "doc_id": forms.NumberInput(attrs={"class": "form-control"}),
            "nib": forms.TextInput(attrs={"class": "form-control"}),
            "morada": forms.TextInput(attrs={"class": "form-control"}),
            "nacionalidade": forms.TextInput(attrs={"class": "form-control"}),
            "nif": forms.NumberInput(attrs={"class": "form-control"}),
            "curriculo": forms.FileInput(attrs={"class": "form-control"}),
            "contrato": forms.FileInput(attrs={"class": "form-control"}),
            "salario": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "horas_diarias": forms.NumberInput(attrs={"class": "form-control"}),
            "horas_mensais": forms.NumberInput(attrs={"class": "form-control"}),
            "horas_extra": forms.NumberInput(attrs={"class": "form-control"}),
            "horas_trabalhadas_mes": forms.NumberInput(attrs={"class": "form-control"}),
            "horas_total": forms.NumberInput(attrs={"class": "form-control"}),
            "furos": forms.SelectMultiple(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._configurar_empresa(empresa=empresa)

    def clean(self):
        cleaned = super().clean()
        self._validar_furos_empresa_clean(cleaned)
        return cleaned


class EmpregadoCreateForm(forms.ModelForm):
    username = forms.CharField(
        label="Nome de utilizador",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    password = forms.CharField(
        label="Palavra-passe",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="Define a palavra-passe inicial do empregado.",
    )

    class Meta:
        model = Empregados
        fields = ["nome", "funcao", "email", "telefone", "curriculo"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "funcao": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
            "curriculo": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        _atribuir_empresa_instance(self.instance, empresa=self.empresa)

    def clean(self):
        cleaned = super().clean()
        _atribuir_empresa_instance(self.instance, empresa=self.empresa)
        return cleaned

    def clean_telefone(self):
        return _normalizar_telefone(self.cleaned_data.get("telefone"))

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            return email

        if existe_empregado_por_email(email):
            raise forms.ValidationError("Já existe um empregado com este email.")

        if existe_user_por_email(email):
            raise forms.ValidationError("Já existe um utilizador com este email.")

        return email

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()

        if not username:
            raise forms.ValidationError("O nome de utilizador é obrigatório.")

        if existe_user_por_username(username):
            raise forms.ValidationError("Já existe um utilizador com esse nome de utilizador.")

        return username

    def clean_password(self):
        password = self.cleaned_data.get("password")

        if not password:
            raise forms.ValidationError("A palavra-passe é obrigatória.")

        if len(password) < 8:
            raise forms.ValidationError("A palavra-passe deve ter pelo menos 8 caracteres.")

        return password


class EmpregadoUpdateForm(BaseEmpregadoForm):
    class Meta:
        model = Empregados
        fields = [
            "user",
            "furos",
            "nome",
            "funcao",
            "email",
            "data_admissao",
            "numero",
            "data_inicio_contrato",
            "data_fim_contrato",
            "telefone",
            "idade",
            "doc_id",
            "nib",
            "morada",
            "nacionalidade",
            "nif",
            "curriculo",
            "contrato",
            "salario",
            "horas_diarias",
            "horas_mensais",
            "horas_extra",
            "horas_trabalhadas_mes",
            "horas_total",
            "alertas",
        ]
        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "furos": forms.SelectMultiple(attrs={"class": "form-control"}),
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "funcao": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "data_admissao": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "numero": forms.NumberInput(attrs={"class": "form-control"}),
            "data_inicio_contrato": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_fim_contrato": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
            "idade": forms.NumberInput(attrs={"class": "form-control"}),
            "doc_id": forms.NumberInput(attrs={"class": "form-control"}),
            "nib": forms.TextInput(attrs={"class": "form-control"}),
            "morada": forms.TextInput(attrs={"class": "form-control"}),
            "nacionalidade": forms.TextInput(attrs={"class": "form-control"}),
            "nif": forms.NumberInput(attrs={"class": "form-control"}),
            "curriculo": forms.FileInput(attrs={"class": "form-control"}),
            "contrato": forms.FileInput(attrs={"class": "form-control"}),
            "salario": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "horas_diarias": forms.NumberInput(attrs={"class": "form-control"}),
            "horas_mensais": forms.NumberInput(attrs={"class": "form-control"}),
            "horas_extra": forms.NumberInput(attrs={"class": "form-control"}),
            "horas_trabalhadas_mes": forms.NumberInput(attrs={"class": "form-control"}),
            "horas_total": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._configurar_empresa(empresa=empresa)

        alertas_valor = self.initial.get("alertas", self.instance.alertas if self.instance.pk else [])
        self.fields["alertas"].initial = json.dumps(alertas_valor, ensure_ascii=False, indent=2)

        if "user" in self.fields:
            self.fields["user"].queryset = listar_users_disponiveis_para_empregado(
                empregado_pk=self.instance.pk if self.instance.pk else None
            )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and existe_empregado_por_email(email, exclude_pk=self.instance.pk):
            raise forms.ValidationError("Já existe outro empregado com este email.")
        return email

    def clean(self):
        cleaned_data = super().clean()

        self._validar_empresa_instancia("Este empregado não pertence à empresa atual.")
        self._validar_furos_empresa_clean(cleaned_data)

        return cleaned_data


class EmpregadoProjetoForm(forms.ModelForm):
    class Meta:
        model = EmpregadoProjeto
        fields = ["projeto", "data_inicio", "data_fim", "ativo"]
        widgets = {
            "projeto": forms.Select(attrs={"class": "form-control"}),
            "data_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_fim": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, empresa=None, empregado=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        self.empregado = empregado

        if self.empregado is not None:
            self.instance.empregado = self.empregado

        _atribuir_empresa_instance(self.instance, empresa=self.empresa)
        self.fields["projeto"].queryset = _obter_queryset_projetos_empresa(self.empresa)

    def clean(self):
        cleaned = super().clean()
        data_inicio = cleaned.get("data_inicio")
        data_fim = cleaned.get("data_fim")
        ativo = cleaned.get("ativo")
        projeto = cleaned.get("projeto")

        if self.empregado is not None:
            self.instance.empregado = self.empregado

        _atribuir_empresa_instance(self.instance, empresa=self.empresa)

        if self.empresa is not None and projeto and projeto.empresa_id != _resolver_empresa_id(self.empresa):
            self.add_error("projeto", "O projeto selecionado não pertence à empresa atual.")

        if data_inicio and data_fim and data_fim < data_inicio:
            self.add_error("data_fim", "A data de fim não pode ser anterior à data de início.")

        if ativo and data_fim:
            self.add_error("ativo", "Se a ligação está ativa, a data de fim deve ficar vazia.")

        return cleaned


class ProjetoEmpregadoForm(forms.Form):
    empregado = forms.ModelChoiceField(
        queryset=listar_empregados_empresa_qs(None),
        label="Empregado",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    data_inicio = forms.DateField(
        required=False,
        label="Data de início",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    def __init__(self, *args, empresa=None, projeto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        self.projeto = projeto
        self.fields["empregado"].queryset = listar_empregados_empresa_qs(empresa)

    def clean(self):
        cleaned = super().clean()
        empregado = cleaned.get("empregado")

        if self.empresa is not None and empregado and empregado.empresa_id != _resolver_empresa_id(self.empresa):
            self.add_error("empregado", "O empregado selecionado não pertence à empresa atual.")

        if self.projeto is not None and self.empresa is not None:
            if self.projeto.empresa_id != _resolver_empresa_id(self.empresa):
                raise forms.ValidationError("O projeto selecionado não pertence à empresa atual.")

        return cleaned


class EmpregadoFicheiroForm(forms.ModelForm):
    class Meta:
        model = EmpregadoFicheiro
        fields = ["tipo", "titulo", "ficheiro", "observacoes"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-control"}),
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "ficheiro": forms.FileInput(attrs={"class": "form-control"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
