from django import forms

from plataforma.models import Plano


class OnboardingEmpresaForm(forms.Form):
    nome_empresa = forms.CharField(
        label="Nome da empresa",
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    nif = forms.CharField(
        label="NIF",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email_empresa = forms.EmailField(
        label="Email da empresa",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    telefone = forms.CharField(
        label="Telefone",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    morada = forms.CharField(
        label="Morada",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    pais = forms.CharField(
        label="País",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    cidade = forms.CharField(
        label="Cidade",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    observacoes = forms.CharField(
        label="Observações",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    nome_admin = forms.CharField(
        label="Nome do administrador",
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    username_admin = forms.CharField(
        label="Username do administrador",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="Se ficar vazio, será usado o email do administrador.",
    )
    email_admin = forms.EmailField(
        label="Email do administrador",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    password_admin = forms.CharField(
        label="Palavra-passe do administrador",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="Deve ter pelo menos 8 caracteres.",
    )

    plano = forms.ModelChoiceField(
        label="Plano",
        queryset=Plano.objects.filter(ativo=True).order_by("nome"),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    tipo_acesso = forms.ChoiceField(
        label="Tipo de acesso inicial",
        choices=[
            ("empresa_admin", "Empresa Admin"),
            ("empresa_gestor", "Empresa Gestor"),
        ],
        initial="empresa_admin",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    estado_empresa = forms.ChoiceField(
        label="Estado inicial da empresa",
        choices=[
            ("teste", "Teste"),
            ("ativa", "Ativa"),
            ("suspensa", "Suspensa"),
        ],
        initial="teste",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    criar_subscricao_inicial = forms.BooleanField(
        label="Criar subscrição inicial",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    valor_subscricao = forms.DecimalField(
        label="Valor da subscrição",
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    criar_pagamento_inicial = forms.BooleanField(
        label="Criar pagamento inicial",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    valor_pagamento = forms.DecimalField(
        label="Valor do pagamento",
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    def clean_nome_empresa(self):
        valor = self.cleaned_data.get("nome_empresa", "").strip()
        if len(valor) < 2:
            raise forms.ValidationError("O nome da empresa deve ter pelo menos 2 caracteres.")
        return valor

    def clean_nome_admin(self):
        valor = self.cleaned_data.get("nome_admin", "").strip()
        if len(valor) < 3:
            raise forms.ValidationError("O nome do administrador deve ter pelo menos 3 caracteres.")
        return valor

    def clean_username_admin(self):
        valor = self.cleaned_data.get("username_admin", "")
        return valor.strip()

    def clean_password_admin(self):
        valor = self.cleaned_data.get("password_admin") or ""
        if len(valor) < 8:
            raise forms.ValidationError("A palavra-passe deve ter pelo menos 8 caracteres.")
        return valor

    def clean(self):
        cleaned = super().clean()

        plano = cleaned.get("plano")
        criar_subscricao_inicial = cleaned.get("criar_subscricao_inicial")
        criar_pagamento_inicial = cleaned.get("criar_pagamento_inicial")
        valor_subscricao = cleaned.get("valor_subscricao")
        valor_pagamento = cleaned.get("valor_pagamento")

        if criar_subscricao_inicial and not plano:
            self.add_error("plano", "Selecione um plano para criar a subscrição inicial.")

        if not criar_subscricao_inicial and valor_subscricao:
            self.add_error(
                "valor_subscricao",
                "Não pode indicar valor de subscrição sem criar subscrição inicial.",
            )

        if criar_pagamento_inicial and not criar_subscricao_inicial and not valor_pagamento:
            self.add_error(
                "valor_pagamento",
                "Indique o valor do pagamento ou ative a subscrição inicial para o valor ser inferido.",
            )

        return cleaned
