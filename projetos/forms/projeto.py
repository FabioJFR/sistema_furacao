from django import forms
from ..models.projeto import Projeto


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
