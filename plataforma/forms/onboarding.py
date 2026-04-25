from django import forms

from plataforma.selectors.forms import listar_planos_ativos_nome_qs


class OnboardingEmpresaForm(forms.Form):
    PERIODOS_COBRANCA_CHOICES = [
        ("1", "1 mês"),
        ("3", "3 meses"),
        ("6", "6 meses"),
        ("12", "12 meses"),
    ]

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
        queryset=listar_planos_ativos_nome_qs().none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    ciclo_subscricao = forms.ChoiceField(
        label="Período de pagamento do plano",
        choices=PERIODOS_COBRANCA_CHOICES,
        initial="1",
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Define quantos meses ficam cobertos por cada pagamento e como será calculada a próxima renovação.",
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
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "step": "0.01",
                "readonly": "readonly",
            }
        ),
        help_text="Calculado automaticamente a partir do plano e do período de pagamento.",
    )

    @staticmethod
    def _calcular_valor_plano(plano, ciclo_subscricao):
        if not plano:
            return None

        try:
            periodo_meses = int(ciclo_subscricao or 1)
        except (TypeError, ValueError):
            periodo_meses = 1

        if periodo_meses == 12:
            if plano.preco_anual:
                return plano.preco_anual
            return (plano.preco_mensal or 0) * 12

        return (plano.preco_mensal or 0) * periodo_meses

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plano"].queryset = listar_planos_ativos_nome_qs()

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
        ciclo_subscricao = cleaned.get("ciclo_subscricao") or "1"
        criar_subscricao_inicial = cleaned.get("criar_subscricao_inicial")

        if criar_subscricao_inicial and not plano:
            self.add_error("plano", "Selecione um plano para criar a subscrição inicial.")

        if criar_subscricao_inicial and plano and int(ciclo_subscricao) not in plano.periodos_cobranca_disponiveis_normalizados:
            self.add_error(
                "ciclo_subscricao",
                "O plano selecionado não permite esse período de cobrança.",
            )

        if criar_subscricao_inicial and plano and int(ciclo_subscricao) in [1, 3, 6] and not plano.preco_mensal:
            self.add_error(
                "ciclo_subscricao",
                "O plano selecionado precisa de preço mensal para períodos de 1, 3 ou 6 meses.",
            )

        if criar_subscricao_inicial and plano and int(ciclo_subscricao) == 12 and not plano.preco_anual and not plano.preco_mensal:
            self.add_error(
                "ciclo_subscricao",
                "O plano selecionado precisa de preço anual ou mensal para 12 meses.",
            )

        valor_calculado = self._calcular_valor_plano(plano, ciclo_subscricao)

        if criar_subscricao_inicial:
            cleaned["valor_subscricao"] = valor_calculado
        else:
            cleaned["valor_subscricao"] = None

        cleaned["valor_pagamento"] = None

        return cleaned
