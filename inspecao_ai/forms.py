from django import forms

from projetos.models import Furo, Projeto

from .models import AnaliseImagemAI


class AnaliseImagemAIForm(forms.ModelForm):
    ROTACAO_CHOICES = [
        ("0", "Sem rotação manual"),
        ("-15", "Rodar -15°"),
        ("-10", "Rodar -10°"),
        ("-5", "Rodar -5°"),
        ("5", "Rodar +5°"),
        ("10", "Rodar +10°"),
        ("15", "Rodar +15°"),
        ("90", "Rodar +90°"),
        ("180", "Rodar 180°"),
        ("270", "Rodar 270°"),
    ]

    auto_corrigir_inclinacao = forms.BooleanField(
        required=False,
        initial=True,
        label="Corrigir inclinação automaticamente",
    )
    rotacao_manual = forms.ChoiceField(
        choices=ROTACAO_CHOICES,
        required=False,
        initial="0",
        label="Rotação manual",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = AnaliseImagemAI
        fields = [
            "nome",
            "tipo_documento",
            "projeto",
            "furo",
            "imagem_original",
            "observacoes",
        ]
        widgets = {
            "nome": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ex.: Caixa NQ Furo 3 - Foto 01"}
            ),
            "tipo_documento": forms.Select(attrs={"class": "form-control"}),
            "projeto": forms.Select(attrs={"class": "form-control"}),
            "furo": forms.Select(attrs={"class": "form-control"}),
            "imagem_original": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "observacoes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Notas sobre a fotografia, caixa, marcador ou contexto do registo.",
                }
            ),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa

        if empresa is not None and not self.instance.empresa_id:
            self.instance.empresa = empresa

        projetos_qs = Projeto.objects.none()
        furos_qs = Furo.objects.none()
        if empresa is not None:
            projetos_qs = Projeto.objects.filter(empresa=empresa).order_by("nome")
            furos_qs = Furo.objects.filter(empresa=empresa).select_related("projeto").order_by(
                "projeto__nome", "nome"
            )

        self.fields["projeto"].queryset = projetos_qs
        self.fields["furo"].queryset = furos_qs
        self.fields["projeto"].required = False
        self.fields["furo"].required = False

    def clean(self):
        cleaned_data = super().clean()
        projeto = cleaned_data.get("projeto")
        furo = cleaned_data.get("furo")

        if furo and projeto and furo.projeto_id != projeto.pk:
            self.add_error("furo", "O furo selecionado não pertence ao projeto escolhido.")

        return cleaned_data
