from django import forms
import json
from .models import Projeto, Furo, Empregados, EmpregadoProjeto, EmpregadoFicheiro, RegistoDiarioEmpregado, Maquina, Material, Medicao, LevantamentoMaterial, DevolucaoMaterial
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class ProjetoForm(forms.ModelForm):
    class Meta:
        model = Projeto
        fields = ['nome', 'cliente', 'cidade', 'pais', 'status', 'notas']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome do projeto'}),
            'cliente': forms.TextInput(attrs={'placeholder': 'Cliente'}),
            'cidade': forms.TextInput(attrs={'placeholder': 'Ex: Aljustrel'}),
            'pais': forms.TextInput(attrs={'placeholder': 'Ex: Portugal'}),
            'notas': forms.Textarea(attrs={'rows': 3}),
            'status': forms.Select(),
        }


# ---------------- Furo ----------------
class FuroForm(forms.ModelForm):
    class Meta:
        model = Furo
        fields = [
            'projeto',
            'nome',
            'tipo',
            'estado',

            'profundidade_inicial',
            'profundidade_alvo',
            'profundidade_atual',
            'profundidade_final',

            'inclinacao',
            'azimute',
            'magnetismo',

            'latitude',
            'longitude',
            'altitude',

            'origem_este',
            'origem_norte',
            'origem_tvd',

            'sistema_coordenadas',
            'localizacao',
            'local_sondagem',
            'detalhes',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),

            'profundidade_inicial': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'profundidade_alvo': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'profundidade_atual': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'profundidade_final': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),

            'inclinacao': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'azimute': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'magnetismo': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),

            'latitude': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'longitude': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'altitude': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),

            'origem_este': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'origem_norte': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'origem_tvd': forms.NumberInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),

            'sistema_coordenadas': forms.Select(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'localizacao': forms.TextInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'local_sondagem': forms.TextInput(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black'}),
            'detalhes': forms.Textarea(attrs={'class': 'p-2 rounded border border-gray-400 bg-white text-black', 'rows': 3}),
        }

    def clean_inclinacao(self):
        valor = self.cleaned_data.get('inclinacao')
        if valor is not None and not (-90 <= valor <= 90):
            raise forms.ValidationError("A inclinação deve estar entre -90° e 90°.")
        return valor

    def clean_azimute(self):
        valor = self.cleaned_data.get('azimute')
        if valor is not None and not (0 <= valor <= 360):
            raise forms.ValidationError("O azimute deve estar entre 0 e 360°.")
        return valor

    def clean_latitude(self):
        valor = self.cleaned_data.get('latitude')
        if valor is not None and not (-90 <= valor <= 90):
            raise forms.ValidationError("Latitude deve estar entre -90 e 90.")
        return valor

    def clean_longitude(self):
        valor = self.cleaned_data.get('longitude')
        if valor is not None and not (-180 <= valor <= 180):
            raise forms.ValidationError("Longitude deve estar entre -180 e 180.")
        return valor

    def clean(self):
        cleaned = super().clean()

        pi = cleaned.get('profundidade_inicial')
        pa = cleaned.get('profundidade_alvo')
        pat = cleaned.get('profundidade_atual')
        pf = cleaned.get('profundidade_final')

        for campo_nome, valor in [
            ('profundidade_inicial', pi),
            ('profundidade_alvo', pa),
            ('profundidade_atual', pat),
            ('profundidade_final', pf),
        ]:
            if valor is not None and valor < 0:
                self.add_error(campo_nome, "O valor não pode ser negativo.")

        if pi is not None and pa is not None and pa < pi:
            self.add_error('profundidade_alvo', "A profundidade alvo não pode ser menor que a profundidade inicial.")

        if pi is not None and pat is not None and pat < pi:
            self.add_error('profundidade_atual', "A profundidade atual não pode ser menor que a profundidade inicial.")

        if pat is not None and pf is not None and pf < pat:
            self.add_error('profundidade_final', "A profundidade final não pode ser menor que a profundidade atual.")

        return cleaned


class FuroCreateForm(forms.ModelForm):
    class Meta:
        model = Furo
        fields = [
            'projeto',
            'tipo',
            'nome',
            'estado',

            'profundidade_inicial',
            'profundidade_alvo',

            'inclinacao',
            'azimute',
            'magnetismo',

            'latitude',
            'longitude',
            'altitude',

            'origem_este',
            'origem_norte',
            'origem_tvd',
            'sistema_coordenadas',

            'localizacao',
            'local_sondagem',
            'detalhes',
        ]
        widgets = {
            'projeto': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),

            'profundidade_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),
            'profundidade_alvo': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),

            'inclinacao': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),
            'azimute': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),
            'magnetismo': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),

            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.000001}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.000001}),
            'altitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),

            'origem_este': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),
            'origem_norte': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),
            'origem_tvd': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),
            'sistema_coordenadas': forms.Select(attrs={'class': 'form-control'}),

            'localizacao': forms.TextInput(attrs={'class': 'form-control'}),
            'local_sondagem': forms.TextInput(attrs={'class': 'form-control'}),
            'detalhes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_inclinacao(self):
        valor = self.cleaned_data.get('inclinacao')
        if valor is not None and not (-90 <= valor <= 90):
            raise forms.ValidationError("A inclinação deve estar entre -90° e 90°.")
        return valor

    def clean_azimute(self):
        valor = self.cleaned_data.get('azimute')
        if valor is not None and not (0 <= valor <= 360):
            raise forms.ValidationError("O azimute deve estar entre 0 e 360°.")
        return valor

    def clean_latitude(self):
        valor = self.cleaned_data.get('latitude')
        if valor is not None and not (-90 <= valor <= 90):
            raise forms.ValidationError("Latitude deve estar entre -90 e 90.")
        return valor

    def clean_longitude(self):
        valor = self.cleaned_data.get('longitude')
        if valor is not None and not (-180 <= valor <= 180):
            raise forms.ValidationError("Longitude deve estar entre -180 e 180.")
        return valor

    def clean(self):
        cleaned = super().clean()

        pi = cleaned.get('profundidade_inicial')
        pa = cleaned.get('profundidade_alvo')

        if pi is not None and pi < 0:
            self.add_error('profundidade_inicial', "A profundidade inicial não pode ser negativa.")

        if pa is not None and pa < 0:
            self.add_error('profundidade_alvo', "A profundidade alvo não pode ser negativa.")

        if pi is not None and pa is not None and pa < pi:
            self.add_error('profundidade_alvo', "A profundidade alvo não pode ser menor que a profundidade inicial.")

        return cleaned


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
    funcao = forms.CharField(
        label="Função",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
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
            'funcao': forms.TextInput(attrs={'class': 'form-control'}),
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
            'funcao': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'curriculo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_telefone(self):
        valor = self.cleaned_data.get('telefone')
        if valor:
            return str(valor).strip()
        return valor


class EmpregadoUpdateForm(forms.ModelForm):
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
            'funcao': forms.TextInput(attrs={'class': 'form-control'}),
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
        data = self.cleaned_data.get('alertas', '[]')
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError('JSON inválido para alertas')

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

class RegistoDiarioEmpregadoForm(forms.ModelForm):
    class Meta:
        model = RegistoDiarioEmpregado
        fields = [
            'projeto',
            'furo',
            'data',
            'hora_inicio',
            'hora_inicio_pausa',
            'hora_fim_pausa',
            'hora_fim',
            'horas_paragem',
            'tipo_paragem',
            'metros_furados',
            'relatorio_foto',
            'observacoes'
        ]
        widgets = {
            'projeto': forms.Select(attrs={'class': 'form-control'}),
            'furo': forms.Select(attrs={'class': 'form-control'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_inicio_pausa': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fim_pausa': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fim': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'horas_paragem': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Horas de paragem'
            }),
            'tipo_paragem': forms.Select(attrs={'class': 'form-control'}),
            'metros_furados': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'relatorio_foto': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, empregado=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empregado = empregado

        if empregado:
            projetos_atuais = empregado.projetos_atuais
            self.fields['projeto'].queryset = projetos_atuais
            self.fields['furo'].queryset = Furo.objects.filter(
                projeto__in=projetos_atuais
            ).distinct()

    def clean_metros_furados(self):
        valor = self.cleaned_data.get('metros_furados')
        if valor is not None and valor < 0:
            raise forms.ValidationError("Os metros furados não podem ser negativos.")
        return valor

    def clean_horas_paragem(self):
        valor = self.cleaned_data.get('horas_paragem')
        if valor is not None and valor < 0:
            raise forms.ValidationError("As horas de paragem não podem ser negativas.")
        return valor

    def clean(self):
        cleaned = super().clean()
        projeto = cleaned.get('projeto')
        furo = cleaned.get('furo')
        hora_inicio = cleaned.get('hora_inicio')
        hora_inicio_pausa = cleaned.get('hora_inicio_pausa')
        hora_fim_pausa = cleaned.get('hora_fim_pausa')
        hora_fim = cleaned.get('hora_fim')
        horas_paragem = cleaned.get('horas_paragem')
        tipo_paragem = cleaned.get('tipo_paragem')

        if furo and projeto and furo.projeto_id != projeto.id:
            self.add_error('furo', 'O furo selecionado não pertence ao projeto escolhido.')

        if hora_inicio and hora_inicio_pausa and hora_inicio_pausa <= hora_inicio:
            self.add_error('hora_inicio_pausa', 'A pausa deve começar depois da hora de início.')

        if hora_inicio_pausa and hora_fim_pausa and hora_fim_pausa <= hora_inicio_pausa:
            self.add_error('hora_fim_pausa', 'A pausa deve terminar depois de começar.')

        if hora_fim_pausa and hora_fim and hora_fim <= hora_fim_pausa:
            self.add_error('hora_fim', 'A hora de fim deve ser posterior ao fim da pausa.')

        if horas_paragem and horas_paragem > 0 and not tipo_paragem:
            self.add_error('tipo_paragem', 'Selecione se a paragem é Cliente ou Empresa.')

        return cleaned


# ---------------- Máquinas ----------------
class MaquinaForm(forms.ModelForm):

    class Meta:
        model = Maquina
        fields = '__all__'

        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),

            'projetos': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'projeto_atual': forms.Select(attrs={'class': 'form-control'}),
            'furos': forms.SelectMultiple(attrs={'class': 'form-control'}),

            'data_compra': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_registo': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_revisao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),

            'matricula': forms.TextInput(attrs={'class': 'form-control'}),
            'seguro': forms.TextInput(attrs={'class': 'form-control'}),
            'data_seguro': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_iuc': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),

            'km': forms.NumberInput(attrs={'class': 'form-control'}),
            'horimetro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'ano_registo': forms.NumberInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),

            'localizacao_atual': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

            'estado': forms.Select(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

        labels = {
            'nome': 'Nome da Máquina',
            'tipo': 'Tipo',
            'marca': 'Marca',
            'modelo': 'Modelo',
            'numero_serie': 'Nº Série',
            'km': 'Quilómetros',
            'horimetro': 'Horímetro',
            'valor': 'Valor (€)',
            'localizacao_atual': 'Localização Atual',
            'projeto_atual': 'Projeto Atual',
            'data_compra': 'Data de Compra',
            'data_registo': 'Data de Registo',
            'data_revisao': 'Data de Revisão',
            'data_seguro': 'Validade do Seguro',
            'data_iuc': 'Validade do IUC',
        }

    # ---------------- INIT ----------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['projeto_atual'].queryset = self.instance.projetos.all()

    # ---------------- VALIDAÇÕES ----------------

    def clean_km(self):
        valor = self.cleaned_data.get('km')
        if valor is not None and valor < 0:
            raise forms.ValidationError("Os quilómetros não podem ser negativos.")
        return valor

    def clean_horimetro(self):
        valor = self.cleaned_data.get('horimetro')
        if valor is not None and valor < 0:
            raise forms.ValidationError("O horímetro não pode ser negativo.")
        return valor

    def clean_valor(self):
        valor = self.cleaned_data.get('valor')
        if valor is not None and valor < 0:
            raise forms.ValidationError("O valor não pode ser negativo.")
        return valor

    def clean_ano_registo(self):
        valor = self.cleaned_data.get('ano_registo')
        if valor is not None and valor < 1900:
            raise forms.ValidationError("Ano inválido.")
        return valor

    def clean(self):
        cleaned = super().clean()

        projeto_atual = cleaned.get('projeto_atual')
        projetos = cleaned.get('projetos')

        data_compra = cleaned.get('data_compra')
        data_revisao = cleaned.get('data_revisao')
        data_seguro = cleaned.get('data_seguro')
        data_iuc = cleaned.get('data_iuc')

        # 🔹 Projeto atual tem de estar nos projetos
        if projeto_atual and projetos and projeto_atual not in projetos:
            self.add_error('projeto_atual', 'O projeto atual deve estar na lista de projetos da máquina.')

        # 🔹 Datas coerentes
        if data_compra and data_revisao and data_revisao < data_compra:
            self.add_error('data_revisao', 'A revisão não pode ser anterior à compra.')

        # 🔹 Avisos úteis (não bloqueiam)
        if data_seguro and data_iuc:
            if data_seguro < data_iuc:
                pass  # aqui podes futuramente lançar warning (não erro)

        return cleaned


# ---------------- Materiais ----------------
class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = '__all__'

        widgets = {
            'projeto': forms.Select(attrs={'class': 'form-control'}),
            'furo': forms.Select(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'unidade': forms.TextInput(attrs={'class': 'form-control'}),
            'diametro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fornecedor': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'localizacao': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'data_compra': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

        labels = {
            'nome': 'Nome do Material',
            'tipo': 'Tipo',
            'marca': 'Marca',
            'numero_serie': 'Nº Série',
            'quantidade': 'Quantidade',
            'unidade': 'Unidade',
            'diametro': 'Diâmetro',
            'valor': 'Valor (€)',
            'fornecedor': 'Fornecedor',
            'localizacao': 'Localização',
            'data_compra': 'Data de Compra',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # furo não obrigatório
        self.fields['furo'].required = False

        if self.instance and self.instance.pk and self.instance.projeto_id:
            self.fields['furo'].queryset = Furo.objects.filter(
                projeto_id=self.instance.projeto_id
            )
        else:
            self.fields['furo'].queryset = Furo.objects.none()


    def clean_quantidade(self):
        valor = self.cleaned_data.get('quantidade')
        if valor is not None and valor < 0:
            raise forms.ValidationError("A quantidade não pode ser negativa.")
        return valor

    def clean_valor(self):
        valor = self.cleaned_data.get('valor')
        if valor is not None and valor < 0:
            raise forms.ValidationError("O valor não pode ser negativo.")
        return valor

    def clean_diametro(self):
        valor = self.cleaned_data.get('diametro')
        if valor is not None and valor < 0:
            raise forms.ValidationError("O diâmetro não pode ser negativo.")
        return valor

    def clean(self):
        cleaned = super().clean()
        projeto = cleaned.get('projeto')
        furo = cleaned.get('furo')

        if furo and projeto and furo.projeto_id != projeto.id:
            self.add_error('furo', 'O furo selecionado não pertence ao projeto.')

        return cleaned

# ---------------- Medições ----------------
class MedicaoForm(forms.ModelForm):
    def __init__(self, *args, furo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.furo = furo

    class Meta:
        model = Medicao
        fields = [
            'profundidade',
            'inclinacao',
            'azimute',
            'magnetismo',
            'imagem',
            'latitude',
            'longitude',
            'altitude',
            'observacoes',
        ]
        widgets = {
            'profundidade': forms.NumberInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'inclinacao': forms.NumberInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'azimute': forms.NumberInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'magnetismo': forms.NumberInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'imagem': forms.FileInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'latitude': forms.NumberInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'longitude': forms.NumberInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'altitude': forms.NumberInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'observacoes': forms.Textarea(attrs={'class': 'border rounded px-3 py-2 w-full', 'rows': 3}),
        }

    def clean_profundidade(self):
        p = self.cleaned_data.get('profundidade')
        if p is None or p < 0:
            raise forms.ValidationError("Profundidade inválida.")
        return p

    def clean_inclinacao(self):
        valor = self.cleaned_data.get('inclinacao')
        if valor is not None and not (-90 <= valor <= 90):
            raise forms.ValidationError("A inclinação deve estar entre -90° e 90°.")
        return valor

    def clean_azimute(self):
        a = self.cleaned_data.get('azimute')
        if a is not None and not (0 <= a <= 360):
            raise forms.ValidationError("Azimute deve estar entre 0 e 360°.")
        return a

    def clean_latitude(self):
        valor = self.cleaned_data.get('latitude')
        if valor is not None and not (-90 <= valor <= 90):
            raise forms.ValidationError("Latitude deve estar entre -90 e 90.")
        return valor

    def clean_longitude(self):
        valor = self.cleaned_data.get('longitude')
        if valor is not None and not (-180 <= valor <= 180):
            raise forms.ValidationError("Longitude deve estar entre -180 e 180.")
        return valor

    def clean(self):
        cleaned = super().clean()
        profundidade = cleaned.get("profundidade")

        if self.furo and profundidade is not None:
            qs = self.furo.medicoes.all()

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            ultima = qs.order_by("-profundidade").first()
            if ultima and ultima.profundidade is not None:
                if profundidade <= ultima.profundidade:
                    raise forms.ValidationError(
                        f"A profundidade deve ser maior que a última medição ({ultima.profundidade} m)."
                    )

        return cleaned
    

# ------------- Registo Diario Empregado Admin -------- #

class RegistoDiarioEmpregadoAdminForm(forms.ModelForm):

    class Meta:
        model = RegistoDiarioEmpregado
        fields = [
            'empregado',
            'projeto',
            'furo',
            'data',
            'hora_inicio',
            'hora_inicio_pausa',
            'hora_fim_pausa',
            'hora_fim',
            'horas_paragem',
            'tipo_paragem',
            'metros_furados',
            'relatorio_foto',
            'observacoes'
        ]
        widgets = {
            'empregado': forms.Select(attrs={'class': 'form-control'}),
            'projeto': forms.Select(attrs={'class': 'form-control'}),
            'furo': forms.Select(attrs={'class': 'form-control'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_inicio_pausa': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fim_pausa': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fim': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'horas_paragem': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tipo_paragem': forms.Select(attrs={'class': 'form-control'}),
            'metros_furados': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'relatorio_foto': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def clean_metros_furados(self):
        valor = self.cleaned_data.get('metros_furados')
        if valor is not None and valor < 0:
            raise forms.ValidationError("Os metros furados não podem ser negativos.")
        return valor

    def clean_horas_paragem(self):
        valor = self.cleaned_data.get('horas_paragem')
        if valor is not None and valor < 0:
            raise forms.ValidationError("As horas de paragem não podem ser negativas.")
        return valor

    def clean(self):
        cleaned = super().clean()
        projeto = cleaned.get('projeto')
        furo = cleaned.get('furo')
        hora_inicio = cleaned.get('hora_inicio')
        hora_inicio_pausa = cleaned.get('hora_inicio_pausa')
        hora_fim_pausa = cleaned.get('hora_fim_pausa')
        hora_fim = cleaned.get('hora_fim')
        horas_paragem = cleaned.get('horas_paragem')
        tipo_paragem = cleaned.get('tipo_paragem')

        if furo and projeto and furo.projeto_id != projeto.id:
            self.add_error('furo', 'O furo selecionado não pertence ao projeto escolhido.')

        if hora_inicio and hora_inicio_pausa and hora_inicio_pausa <= hora_inicio:
            self.add_error('hora_inicio_pausa', 'A pausa deve começar depois da hora de início.')

        if hora_inicio_pausa and hora_fim_pausa and hora_fim_pausa <= hora_inicio_pausa:
            self.add_error('hora_fim_pausa', 'A pausa deve terminar depois de começar.')

        if hora_fim_pausa and hora_fim and hora_fim <= hora_fim_pausa:
            self.add_error('hora_fim', 'A hora de fim deve ser posterior ao fim da pausa.')

        if horas_paragem and horas_paragem > 0 and not tipo_paragem:
            self.add_error('tipo_paragem', 'Selecione se a paragem é Cliente ou Empresa.')

        return cleaned

# ------------ Levantamento Material ----------------- #

class LevantamentoMaterialForm(forms.ModelForm):
    class Meta:
        model = LevantamentoMaterial
        fields = ['material', 'projeto', 'furo', 'quantidade', 'data', 'observacoes']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-control'}),
            'projeto': forms.Select(attrs={'class': 'form-control'}),
            'furo': forms.Select(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empregado=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empregado = empregado

        self.fields['furo'].required = False

        # só materiais ativos e com stock
        self.fields['material'].queryset = Material.objects.filter(
            ativo=True,
            quantidade__gt=0
        ).order_by('nome')

        if empregado:
            projetos_atuais = empregado.projetos_atuais
            self.fields['projeto'].queryset = projetos_atuais
            self.fields['furo'].queryset = Furo.objects.filter(
                projeto__in=projetos_atuais
            ).distinct()
        else:
            self.fields['projeto'].queryset = Projeto.objects.none()
            self.fields['furo'].queryset = Furo.objects.none()

    def clean_quantidade(self):
        quantidade = self.cleaned_data.get('quantidade')
        material = self.cleaned_data.get('material')

        if quantidade is None or quantidade <= 0:
            raise forms.ValidationError("A quantidade deve ser maior que zero.")

        if material and quantidade > material.quantidade:
            raise forms.ValidationError("Quantidade superior ao stock disponível.")

        return quantidade

    def clean(self):
        cleaned = super().clean()
        projeto = cleaned.get('projeto')
        furo = cleaned.get('furo')

        if furo and projeto and furo.projeto_id != projeto.id:
            self.add_error('furo', 'O furo selecionado não pertence ao projeto.')

        return cleaned
    

# -------------- Devolução Material ----------------- #

class DevolucaoMaterialForm(forms.ModelForm):
    class Meta:
        model = DevolucaoMaterial
        fields = ['material', 'projeto', 'furo', 'quantidade', 'data', 'observacoes']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-control'}),
            'projeto': forms.Select(attrs={'class': 'form-control'}),
            'furo': forms.Select(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empregado=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empregado = empregado

        self.fields['furo'].required = False

        self.fields['material'].queryset = Material.objects.filter(
            ativo=True
        ).order_by('nome')

        if empregado:
            projetos_atuais = empregado.projetos_atuais
            self.fields['projeto'].queryset = projetos_atuais
            self.fields['furo'].queryset = Furo.objects.filter(
                projeto__in=projetos_atuais
            ).distinct()
        else:
            self.fields['projeto'].queryset = Projeto.objects.none()
            self.fields['furo'].queryset = Furo.objects.none()

    def clean_quantidade(self):
        quantidade = self.cleaned_data.get('quantidade')

        if quantidade is None or quantidade <= 0:
            raise forms.ValidationError("A quantidade deve ser maior que zero.")

        return quantidade

    def clean(self):
        cleaned = super().clean()
        projeto = cleaned.get('projeto')
        furo = cleaned.get('furo')

        if furo and projeto and furo.projeto_id != projeto.id:
            self.add_error('furo', 'O furo selecionado não pertence ao projeto.')

        return cleaned