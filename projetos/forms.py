from django import forms
import json
from .models import Projeto, Furo, Empregados, Maquina, Material, Medicao, EmpregadoProjeto, EmpregadoFicheiro


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


# ---------------- Máquinas ----------------
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


class MaquinaCreateForm(forms.ModelForm):
    class Meta:
        model = Maquina
        fields = ['nome', 'modelo', 'estado']


class MaquinaUpdateForm(forms.ModelForm):
    class Meta:
        model = Maquina
        fields = '__all__'


# ---------------- Materiais ----------------
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