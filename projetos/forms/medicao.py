from django import forms

from ..models.medicao import Medicao



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _atribuir_contexto_medicao(instance, furo=None, empresa=None):
    if furo is not None:
        instance.furo = furo

    if empresa is not None:
        instance.empresa_id = _resolver_empresa_id(empresa)

    return instance



class MedicaoForm(forms.ModelForm):
    def __init__(self, *args, furo=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.furo = furo
        self.empresa = empresa

        _atribuir_contexto_medicao(self.instance, furo=self.furo, empresa=self.empresa)
        if self.furo is not None and not self.is_bound and self.instance._state.adding:
            profundidade_atual = getattr(self.furo, "profundidade_atual", None)
            profundidade_maxima = getattr(self.furo, "profundidade_maxima_atingida", None)
            self.fields["profundidade_medida"].initial = (
                profundidade_atual
                if profundidade_atual not in (None, "")
                else profundidade_maxima
            )

        self.fields["profundidade_medida"].required = True
        self.fields["profundidade_medida"].help_text = "Campo mínimo da medição: profundidade onde a leitura/amostra foi feita."
        self.fields["inclinacao_real_medida"].help_text = "Opcional se ainda não houver leitura de desvio."
        self.fields["azimute_real_medido"].help_text = "Opcional se ainda não houver leitura de azimute."
        self.fields["magnetismo"].help_text = "Opcional no primeiro uso; preenche quando houver leitura real."
        self.fields["tipo_rocha"].help_text = "Opcional: descrição simples da rocha/amostra observada."
        self.fields["observacoes"].help_text = "Notas livres para ajudar a interpretar a medição no relatório."

    class Meta:
        model = Medicao
        fields = [
            "profundidade_medida",
            "inclinacao_real_medida",
            "azimute_real_medido",
            "magnetismo",
            "imagem",
            "latitude",
            "longitude",
            "altitude",
            "tipo_rocha",
            "cor",
            "dureza",
            "observacoes",
        ]
        widgets = {
            "profundidade_medida": forms.NumberInput(attrs={"step": 0.01}),
            "inclinacao_real_medida": forms.NumberInput(attrs={"step": 0.01}),
            "azimute_real_medido": forms.NumberInput(attrs={"step": 0.01}),
            "magnetismo": forms.NumberInput(attrs={"step": 0.01}),
            "imagem": forms.FileInput(),
            "latitude": forms.NumberInput(attrs={"step": 0.000001}),
            "longitude": forms.NumberInput(attrs={"step": 0.000001}),
            "altitude": forms.NumberInput(attrs={"step": 0.01}),
            "tipo_rocha": forms.TextInput(),
            "cor": forms.TextInput(),
            "dureza": forms.NumberInput(attrs={"step": 0.01}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_profundidade_medida(self):
        valor = self.cleaned_data.get("profundidade_medida")
        if valor is None or valor < 0:
            raise forms.ValidationError("Profundidade medida inválida.")
        return valor

    def clean_inclinacao_real_medida(self):
        valor = self.cleaned_data.get("inclinacao_real_medida")
        if valor is not None and not (-90 <= valor <= 90):
            raise forms.ValidationError("A inclinação real medida deve estar entre -90° e 90°.")
        return valor

    def clean_azimute_real_medido(self):
        valor = self.cleaned_data.get("azimute_real_medido")
        if valor is not None and not (0 <= valor <= 360):
            raise forms.ValidationError("O azimute real medido deve estar entre 0 e 360°.")
        return valor

    def clean_latitude(self):
        valor = self.cleaned_data.get("latitude")
        if valor is not None and not (-90 <= valor <= 90):
            raise forms.ValidationError("Latitude deve estar entre -90 e 90.")
        return valor

    def clean_longitude(self):
        valor = self.cleaned_data.get("longitude")
        if valor is not None and not (-180 <= valor <= 180):
            raise forms.ValidationError("Longitude deve estar entre -180 e 180.")
        return valor

    def clean_dureza(self):
        valor = self.cleaned_data.get("dureza")
        if valor is not None and valor < 0:
            raise forms.ValidationError("A dureza não pode ser negativa.")
        return valor

    def clean(self):
        cleaned = super().clean()
        _atribuir_contexto_medicao(self.instance, furo=self.furo, empresa=self.empresa)

        if self.instance and self.instance.pk and self.empresa is not None:
            empresa_id = _resolver_empresa_id(self.empresa)
            if self.instance.empresa_id and self.instance.empresa_id != empresa_id:
                raise forms.ValidationError(
                    "A medição selecionada não pertence à empresa atual."
                )

        if self.furo and self.empresa is not None:
            empresa_id = _resolver_empresa_id(self.empresa)
            if self.furo.empresa_id != empresa_id:
                raise forms.ValidationError(
                    "O furo selecionado não pertence à empresa atual."
                )

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        _atribuir_contexto_medicao(instance, furo=self.furo, empresa=self.empresa)

        if commit:
            instance.save()

        return instance
