from django import forms
from .models import Projeto, Furo, Empregados, Maquina, Material, Medicao
import json


class ProjetoForm(forms.ModelForm):
    class Meta:
        model = Projeto
        fields = ['nome', 'cliente', 'cidade', 'pais', 'status', 'notas']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome do projeto'}),
            'cliente': forms.TextInput(attrs={'placeholder': 'Cliente'}),
            'cidade': forms.TextInput(attrs={'placeholder': 'Cidade'}),
            'pais': forms.TextInput(attrs={'placeholder': 'País'}),
            'notas': forms.Textarea(attrs={'rows': 3}),
            'status': forms.Select()
        }


# Formulario do Furo

class FuroForm(forms.ModelForm):
    class Meta:
        model = Furo
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(attrs={'class':'p-2 rounded border border-gray-400 bg-white text-black'}),
            'profundidade': forms.NumberInput(attrs={'class':'p-2 rounded border border-gray-400 bg-white text-black'}),
            'inclinacao': forms.NumberInput(attrs={'class':'p-2 rounded border border-gray-400 bg-white text-black'}),
            'azimute': forms.NumberInput(attrs={'class':'p-2 rounded border border-gray-400 bg-white text-black'}),
            'magnetismo': forms.NumberInput(attrs={'class':'p-2 rounded border border-gray-400 bg-white text-black'}),
            'latitude': forms.NumberInput(attrs={'class':'p-2 rounded border border-gray-400 bg-white text-black'}),
            'longitude': forms.NumberInput(attrs={'class':'p-2 rounded border border-gray-400 bg-white text-black'}),
            'altitude': forms.NumberInput(attrs={'class':'p-2 rounded border border-gray-400 bg-white text-black'}),
            'data': forms.DateInput(attrs={'class':'p-2 rounded border border-gray-400 bg-white text-black', 'type':'date'}),
        }

class FuroCreateForm(forms.ModelForm):
    class Meta:
        model = Furo
        fields = [
            'projeto',           # Projeto relacionado
            'tipo',              # Tipo de furo
            'nome',              # Nome do furo
            'profundidade_alvo', # Profundidade alvo
            'inclinacao',        # Inclinação
            'azimute',           # Azimute
            'localizacao',       # Localização (coordenadas ou texto)
            'local_sondagem',    # Local da sondagem
            'estado',            # Estado do furo
            'detalhes',          # Detalhes adicionais
        ]
        widgets = {
            'projeto': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'profundidade_alvo': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),
            'inclinacao': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),
            'azimute': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01}),
            'localizacao': forms.TextInput(attrs={'class': 'form-control'}),
            'local_sondagem': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'detalhes': forms.Textarea(attrs={'class': 'form-control', 'rows':3}),
        }


# EMPREGADO FORM
class EmpregadosForm(forms.ModelForm):
    alertas = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text='Lista JSON de alertas'
    )
    projetos_ativos = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text='Lista JSON de IDs de projetos ativos'
    )

    class Meta:
        model = Empregados
        fields = '__all__'

    def clean_alertas(self):
        return self._clean_json('alertas')

    def clean_projetos_ativos(self):
        return self._clean_json('projetos_ativos')

    def _clean_json(self, field_name):
        data = self.cleaned_data.get(field_name, '[]')
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError(f'JSON inválido para {field_name}')

# Formulário para criar empregado (apenas campos essenciais)
class EmpregadoCreateForm(forms.ModelForm):
    class Meta:
        model = Empregados
        fields = ['nome', 'funcao', 'email']  # apenas os campos básicos

# Formulário para editar empregado (todos os campos)
class EmpregadoUpdateForm(forms.ModelForm):
    class Meta:
        model = Empregados
        fields = '__all__'  # todos os campos disponíveis


# Formularop Maquina
class MaquinaForm(forms.ModelForm):
    despesas = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text='Lista JSON de despesas (imagens, ficheiros, etc.)'
    )

    class Meta:
        model = Maquina
        fields = '__all__'

    def clean_despesas(self):
        data = self.cleaned_data.get('despesas', '[]')
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError('JSON inválido para despesas')
        
from django import forms
from .models import Maquina

# Form para criar máquina (campos essenciais)
class MaquinaCreateForm(forms.ModelForm):
    class Meta:
        model = Maquina
        fields = ['nome', 'modelo', 'estado']  # apenas campos obrigatórios

# Form para atualizar máquina (todos os campos)
class MaquinaUpdateForm(forms.ModelForm):
    class Meta:
        model = Maquina
        fields = '__all__'


# MATERIAL FORM
class MaterialForm(forms.ModelForm):
    faturas = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text='Lista JSON de faturas'
    )

    class Meta:
        model = Material
        fields = '__all__'

    def clean_faturas(self):
        data = self.cleaned_data.get('faturas', '[]')
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError('JSON inválido para faturas')



# MEDICAO FORM
class MedicaoForm(forms.ModelForm):
    class Meta:
        model = Medicao
        fields = ['profundidade', 'inclinacao', 'azimute', 'magnetismo', 'nome_furo']
        widgets = {
            'profundidade': forms.NumberInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'inclinacao': forms.NumberInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'azimute': forms.NumberInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'magnetismo': forms.NumberInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'nome_furo': forms.TextInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
        }