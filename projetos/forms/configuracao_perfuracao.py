from django import forms
from projetos.models import ConfiguracaoPerfuracaoEmpregado, Furo


class ConfiguracaoPerfuracaoEmpregadoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoPerfuracaoEmpregado
        fields = [
            "furo",
            "comprimento_tubo",
            "comprimento_karoutier",
            "comprimento_acrescento",
            "comprimento_calibrador",
            "comprimento_record",
            "comprimento_bit",
            "comprimento_caixa_mola",
            "comprimento_tubo_interior",
            "comprimento_cabeca_interior",
        ]
        widgets = {
            "furo": forms.Select(attrs={"class": "form-control"}),
            "comprimento_tubo": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_karoutier": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_acrescento": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_calibrador": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_record": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_bit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_caixa_mola": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_tubo_interior": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_cabeca_interior": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, empregado=None, **kwargs):
        super().__init__(*args, **kwargs)

        if empregado:
            self.fields["furo"].queryset = Furo.objects.filter(empregados=empregado).distinct().order_by("nome")
        else:
            self.fields["furo"].queryset = Furo.objects.all().order_by("nome")
    class Meta:
        model = ConfiguracaoPerfuracaoEmpregado
        fields = [
            "furo",
            "comprimento_tubo",
            "comprimento_karoutier",
            "comprimento_acrescento",
            "comprimento_calibrador",
            "comprimento_record",
            "comprimento_bit",
            "comprimento_caixa_mola",
            "comprimento_tubo_interior",
            "comprimento_cabeca_interior",
        ]
        widgets = {
            "furo": forms.Select(attrs={"class": "form-control"}),
            "comprimento_tubo": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_karoutier": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_acrescento": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_calibrador": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_record": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_bit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_caixa_mola": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_tubo_interior": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_cabeca_interior": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, empregado=None, **kwargs):
        super().__init__(*args, **kwargs)

        if empregado is not None:
            self.fields["furo"].queryset = empregado.furos.all().order_by("nome")

    def clean(self):
        cleaned_data = super().clean()

        for field_name, value in cleaned_data.items():
            if field_name == "furo":
                continue
            if value is not None and value < 0:
                self.add_error(field_name, "O comprimento não pode ser negativo.")

        return cleaned_data