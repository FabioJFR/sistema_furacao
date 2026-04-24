from django import forms

from projetos.models import EmpregadoFuro
from projetos.selectors.forms import listar_empregados_furo_form_qs, resolver_empresa_id



def _resolver_empresa_id(empresa):
    return resolver_empresa_id(empresa)



def _atribuir_contexto_empregado_furo(instance, empresa=None, furo=None):
    if furo is not None:
        instance.furo = furo

    if empresa is not None:
        instance.empresa_id = _resolver_empresa_id(empresa)

    return instance



class EmpregadoFuroForm(forms.ModelForm):
    class Meta:
        model = EmpregadoFuro
        fields = [
            "empregado",
            "funcao",
            "data_inicio",
            "data_fim",
            "ativo",
            "observacoes",
        ]
        widgets = {
            "empregado": forms.Select(attrs={"class": "form-control"}),
            "funcao": forms.Select(attrs={"class": "form-control"}),
            "data_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_fim": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop("empresa", None)
        self.furo = kwargs.pop("furo", None)

        super().__init__(*args, **kwargs)

        _atribuir_contexto_empregado_furo(self.instance, empresa=self.empresa, furo=self.furo)

        self.fields["empregado"].queryset = listar_empregados_furo_form_qs(
            empresa=self.empresa,
            furo=self.furo,
            is_edicao=bool(self.instance.pk),
        )

    def clean(self):
        cleaned = super().clean()
        empregado = cleaned.get("empregado")

        _atribuir_contexto_empregado_furo(self.instance, empresa=self.empresa, furo=self.furo)

        if self.empresa is not None:
            empresa_id = _resolver_empresa_id(self.empresa)

            if empregado and empregado.empresa_id != empresa_id:
                self.add_error("empregado", "O empregado selecionado não pertence à empresa atual.")

            if self.furo is not None and self.furo.empresa_id != empresa_id:
                raise forms.ValidationError("O furo selecionado não pertence à empresa atual.")

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        _atribuir_contexto_empregado_furo(instance, empresa=self.empresa, furo=self.furo)

        if commit:
            instance.save()

        return instance
