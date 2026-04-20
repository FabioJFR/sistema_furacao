from django import forms
from projetos.models import (
    ConfiguracaoPerfuracaoEmpregado,
    Furo,
    EmpregadoFuro,
    RegistoDiarioEmpregado,
)



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


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

    def __init__(self, *args, empregado=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empregado = empregado
        self.empresa = empresa or getattr(empregado, "empresa", None)

        if empregado is not None:
            furo_ids_associados = EmpregadoFuro.objects.filter(
                empregado=empregado
            ).values_list("furo_id", flat=True)

            furo_ids_registos = RegistoDiarioEmpregado.objects.filter(
                empregado=empregado,
                furo__isnull=False,
            ).values_list("furo_id", flat=True)

            furo_ids = list(furo_ids_associados) + list(furo_ids_registos)

            queryset = Furo.objects.filter(id__in=furo_ids)

            if self.empresa is not None:
                empresa_id = _resolver_empresa_id(self.empresa)
                queryset = queryset.filter(empresa_id=empresa_id)

            self.fields["furo"].queryset = queryset.distinct().order_by("nome")
        else:
            self.fields["furo"].queryset = Furo.objects.none()

    def clean(self):
        cleaned_data = super().clean()

        furo = cleaned_data.get("furo")

        if self.empregado is not None and self.empresa is not None:
            empresa_id = _resolver_empresa_id(self.empresa)
            if self.empregado.empresa_id != empresa_id:
                raise forms.ValidationError("O empregado não pertence à empresa atual.")

            if furo and furo.empresa_id != empresa_id:
                self.add_error("furo", "O furo selecionado não pertence à empresa atual.")

        for field_name, value in cleaned_data.items():
            if field_name == "furo":
                continue
            if value is not None and value < 0:
                self.add_error(field_name, "O comprimento não pode ser negativo.")

        return cleaned_data