from django import forms

from geologia.models import AnexoLogGeologico


class AnexoLogGeologicoForm(forms.ModelForm):
    class Meta:
        model = AnexoLogGeologico
        fields = ["tipo", "titulo", "ficheiro", "descricao"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "titulo": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "ficheiro": forms.FileInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "descricao": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 3}),
        }

