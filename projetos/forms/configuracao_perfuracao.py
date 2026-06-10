from django import forms
from projetos.models import (
    ConfiguracaoPerfuracaoEmpregado,
)
from projetos.selectors.forms import listar_furos_configuracao_perfuracao_qs, resolver_empresa_id



def _resolver_empresa_id(empresa):
    return resolver_empresa_id(empresa)


class ConfiguracaoPerfuracaoEmpregadoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoPerfuracaoEmpregado
        fields = [
            "furo",
            "medida_morta",
            "comprimento_tubo",
            "comprimento_karoutier",
            "quantidade_karoutier",
            "comprimento_acrescento",
            "quantidade_acrescento",
            "comprimento_calibrador",
            "quantidade_calibrador",
            "comprimento_record",
            "quantidade_record",
            "comprimento_bit",
            "comprimento_caixa_mola",
            "comprimento_tubo_interior",
            "quantidade_tubo_interior",
            "comprimento_acrescento_tubo_interior",
            "quantidade_acrescento_tubo_interior",
            "comprimento_cabeca_interior",
        ]
        widgets = {
            "furo": forms.Select(attrs={"class": "form-control"}),
            "medida_morta": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_tubo": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_karoutier": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "quantidade_karoutier": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "1"}),
            "comprimento_acrescento": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "quantidade_acrescento": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "1"}),
            "comprimento_calibrador": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "quantidade_calibrador": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "1"}),
            "comprimento_record": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "quantidade_record": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "1"}),
            "comprimento_bit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_caixa_mola": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprimento_tubo_interior": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "quantidade_tubo_interior": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "1"}),
            "comprimento_acrescento_tubo_interior": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "quantidade_acrescento_tubo_interior": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "1"}),
            "comprimento_cabeca_interior": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, empregado=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empregado = empregado
        self.empresa = empresa or getattr(empregado, "empresa", None)

        if empregado is not None:
            self.fields["furo"].queryset = listar_furos_configuracao_perfuracao_qs(
                empregado=empregado,
                empresa=self.empresa,
            )
        else:
            self.fields["furo"].queryset = listar_furos_configuracao_perfuracao_qs(empregado=None, empresa=self.empresa)

        if self.instance and self.instance.pk:
            self.fields["furo"].disabled = True

    def clean(self):
        cleaned_data = super().clean()

        is_edicao = bool(self.instance and self.instance.pk)
        furo = cleaned_data.get("furo")
        if is_edicao:
            furo = self.instance.furo
            cleaned_data["furo"] = furo

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
                if field_name.startswith("quantidade_"):
                    self.add_error(field_name, "A quantidade não pode ser negativa.")
                elif field_name == "medida_morta":
                    self.add_error(field_name, "A medida morta não pode ser negativa.")
                else:
                    self.add_error(field_name, "O comprimento não pode ser negativo.")

        return cleaned_data
