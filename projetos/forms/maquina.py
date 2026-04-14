from django import forms
from ..models.maquina import Maquina


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
