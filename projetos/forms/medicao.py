from django import forms
from ..models.medicao import Medicao


# ---------------- Medições ----------------
class MedicaoForm(forms.ModelForm):
    def __init__(self, *args, furo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.furo = furo

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
            "profundidade_medida": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "inclinacao_real_medida": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "azimute_real_medido": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "magnetismo": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "imagem": forms.FileInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "latitude": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "longitude": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "altitude": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "tipo_rocha": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "cor": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "dureza": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "observacoes": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 3}),
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
        profundidade_medida = cleaned.get("profundidade_medida")

        if self.furo and profundidade_medida is not None:
            qs = self.furo.medicoes.all()

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            ultima = qs.order_by("-profundidade_medida").first()
            if ultima and ultima.profundidade_medida is not None:
                if profundidade_medida <= ultima.profundidade_medida:
                    raise forms.ValidationError(
                        f"A profundidade medida deve ser maior que a última medição ({ultima.profundidade_medida} m)."
                    )

        return cleaned