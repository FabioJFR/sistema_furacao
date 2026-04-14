from django import forms
from ..models.material import Material
from ..models.furo import Furo
from ..models.material import LevantamentoMaterial, DevolucaoMaterial
from ..models.projeto import Projeto


class SaidaMaterialForm(forms.Form):
    quantidade = forms.IntegerField(
        min_value=1,
        label="Quantidade a retirar"
    )


class EntradaMaterialForm(forms.Form):
    quantidade = forms.IntegerField(
        min_value=1,
        label="Quantidade a adicionar"
    )


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