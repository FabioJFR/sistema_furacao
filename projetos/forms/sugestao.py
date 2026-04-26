from django import forms

from projetos.models import SugestaoPlataforma


class SugestaoPlataformaForm(forms.ModelForm):
    class Meta:
        model = SugestaoPlataforma
        fields = ["avaliacao", "opiniao", "sugestoes"]
        widgets = {
            "avaliacao": forms.Select(attrs={"class": "w-full rounded-lg border border-gray-300 px-3 py-2"}),
            "opiniao": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "w-full rounded-lg border border-gray-300 px-3 py-2",
                    "placeholder": "Partilha em poucas palavras o que achas da plataforma.",
                }
            ),
            "sugestoes": forms.Textarea(
                attrs={
                    "rows": 6,
                    "class": "w-full rounded-lg border border-gray-300 px-3 py-2",
                    "placeholder": "Escreve aqui as melhorias que gostavas de ver.",
                }
            ),
        }
        labels = {
            "avaliacao": "O que achas da plataforma?",
            "opiniao": "Opinião geral (opcional)",
            "sugestoes": "Sugestões de melhoria",
        }

