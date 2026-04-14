from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
import json
from ..models.empregado import Empregados, EmpregadoProjeto, EmpregadoFicheiro

# ---------------- Empregados ----------------

class EmpregadoRegistroForm(UserCreationForm):
    username = forms.CharField(
        label="Nome de utilizador",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    nome = forms.CharField(
        label="Nome completo",
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    telefone = forms.CharField(
        label="Telefone",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    funcao = forms.ChoiceField(
        label="Função",
        required=False,
        choices=Empregados._meta.get_field('funcao').choices,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label="Palavra-passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="A palavra-passe deve ter pelo menos 8 caracteres e não deve ser parecida com o nome de utilizador."
    )
    password2 = forms.CharField(
        label="Confirmar palavra-passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Introduza novamente a mesma palavra-passe."
    )

    class Meta:
        model = User
        fields = ['username', 'nome', 'email', 'telefone', 'funcao', 'password1', 'password2']

    def clean_nome(self):
        valor = self.cleaned_data.get('nome', '').strip()
        if len(valor) < 3:
            raise forms.ValidationError("O nome deve ter pelo menos 3 caracteres.")
        return valor

    def clean_telefone(self):
        valor = self.cleaned_data.get('telefone')
        if valor:
            return str(valor).strip()
        return valor
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este email.")
        return email


class EmpregadosForm(forms.ModelForm):
    alertas = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text='Lista JSON de alertas'
    )

    class Meta:
        model = Empregados
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'funcao': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'data_admissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_inicio_contrato': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim_contrato': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'idade': forms.NumberInput(attrs={'class': 'form-control'}),
            'doc_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'nib': forms.TextInput(attrs={'class': 'form-control'}),
            'morada': forms.TextInput(attrs={'class': 'form-control'}),
            'nacionalidade': forms.TextInput(attrs={'class': 'form-control'}),
            'nif': forms.NumberInput(attrs={'class': 'form-control'}),
            'curriculo': forms.FileInput(attrs={'class': 'form-control'}),
            'contrato': forms.FileInput(attrs={'class': 'form-control'}),
            'salario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'horas_diarias': forms.NumberInput(attrs={'class': 'form-control'}),
            'horas_mensais': forms.NumberInput(attrs={'class': 'form-control'}),
            'horas_extra': forms.NumberInput(attrs={'class': 'form-control'}),
            'horas_trabalhadas_mes': forms.NumberInput(attrs={'class': 'form-control'}),
            'horas_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'furos': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

    def clean_alertas(self):
        return self._clean_json('alertas')

    def _clean_json(self, field_name):
        data = self.cleaned_data.get(field_name, '[]')
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError(f'JSON inválido para {field_name}')

    def clean_telefone(self):
        valor = self.cleaned_data.get('telefone')
        if valor:
            return str(valor).strip()
        return valor


class EmpregadoCreateForm(forms.ModelForm):
    class Meta:
        model = Empregados
        fields = ['nome', 'funcao', 'email', 'telefone', 'curriculo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'funcao': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'curriculo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_telefone(self):
        valor = self.cleaned_data.get('telefone')
        if valor:
            return str(valor).strip()
        return valor
    
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            return email

        if Empregados.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe um empregado com este email.")

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe um utilizador com este email.")

        return email


class EmpregadoUpdateForm(forms.ModelForm):
    alertas = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        required=False,
        help_text='Lista JSON de alertas'
    )

    class Meta:
        model = Empregados
        fields = [
            'user',
            'furos',
            'nome',
            'funcao',
            'email',
            'data_admissao',
            'numero',
            'data_inicio_contrato',
            'data_fim_contrato',
            'telefone',
            'idade',
            'doc_id',
            'nib',
            'morada',
            'nacionalidade',
            'nif',
            'curriculo',
            'contrato',
            'salario',
            'horas_diarias',
            'horas_mensais',
            'horas_extra',
            'horas_trabalhadas_mes',
            'horas_total',
            'alertas',
            'aprovado',
            'data_aprovacao',
        ]
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'furos': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'funcao': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'data_admissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'numero': forms.NumberInput(attrs={'class': 'form-control'}),
            'data_inicio_contrato': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim_contrato': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'idade': forms.NumberInput(attrs={'class': 'form-control'}),
            'doc_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'nib': forms.TextInput(attrs={'class': 'form-control'}),
            'morada': forms.TextInput(attrs={'class': 'form-control'}),
            'nacionalidade': forms.TextInput(attrs={'class': 'form-control'}),
            'nif': forms.NumberInput(attrs={'class': 'form-control'}),
            'curriculo': forms.FileInput(attrs={'class': 'form-control'}),
            'contrato': forms.FileInput(attrs={'class': 'form-control'}),
            'salario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'horas_diarias': forms.NumberInput(attrs={'class': 'form-control'}),
            'horas_mensais': forms.NumberInput(attrs={'class': 'form-control'}),
            'horas_extra': forms.NumberInput(attrs={'class': 'form-control'}),
            'horas_trabalhadas_mes': forms.NumberInput(attrs={'class': 'form-control'}),
            'horas_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'aprovado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'data_aprovacao': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        alertas_valor = self.initial.get('alertas', self.instance.alertas if self.instance.pk else [])
        self.fields['alertas'].initial = json.dumps(alertas_valor, ensure_ascii=False, indent=2)

        if 'user' in self.fields:
            users_ocupados = Empregados.objects.exclude(
                pk=self.instance.pk if self.instance.pk else None
            ).exclude(
                user__isnull=True
            ).values_list('user_id', flat=True)

            self.fields['user'].queryset = User.objects.exclude(id__in=users_ocupados).order_by('username')


    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and Empregados.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Já existe outro empregado com este email.")
        return email


    def clean(self):
        cleaned_data = super().clean()

        aprovado = cleaned_data.get("aprovado")
        data_aprovacao = cleaned_data.get("data_aprovacao")

        if aprovado and not data_aprovacao:
            from django.utils import timezone
            cleaned_data["data_aprovacao"] = timezone.now()

        return cleaned_data

    def clean_alertas(self):
        data = self.cleaned_data.get('alertas', '[]')

        if not data:
            return []

        try:
            valor = json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError('JSON inválido para alertas')

        if not isinstance(valor, list):
            raise forms.ValidationError('O campo alertas deve conter uma lista JSON.')

        return valor

    def clean_telefone(self):
        valor = self.cleaned_data.get('telefone')
        if valor:
            return str(valor).strip()
        return valor


class EmpregadoProjetoForm(forms.ModelForm):
    class Meta:
        model = EmpregadoProjeto
        fields = ['projeto', 'data_inicio', 'data_fim', 'ativo']
        widgets = {
            'projeto': forms.Select(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned = super().clean()
        data_inicio = cleaned.get('data_inicio')
        data_fim = cleaned.get('data_fim')
        ativo = cleaned.get('ativo')

        if data_inicio and data_fim and data_fim < data_inicio:
            self.add_error('data_fim', 'A data de fim não pode ser anterior à data de início.')

        if ativo and data_fim:
            self.add_error('ativo', 'Se a ligação está ativa, a data de fim deve ficar vazia.')

        return cleaned


class EmpregadoFicheiroForm(forms.ModelForm):
    class Meta:
        model = EmpregadoFicheiro
        fields = ['tipo', 'titulo', 'ficheiro', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'ficheiro': forms.FileInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
