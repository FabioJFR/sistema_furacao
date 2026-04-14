from django import forms
from ..models.furo import Furo


class FuroForm(forms.ModelForm):
    class Meta:
        model = Furo
        fields = [
            "projeto",
            "nome",
            "tipo",
            "estado",

            "profundidade_inicial",
            "profundidade_alvo_inicial",
            "profundidade_alvo_atual",
            "profundidade_atual",
            "profundidade_maxima_atingida",

            "inclinacao_planeada_inicial",
            "inclinacao_planeada_atual",
            "azimute_planeado_inicial",
            "azimute_planeado_atual",

            "inclinacao_real_atual",
            "azimute_real_atual",
            "magnetismo",

            "latitude",
            "longitude",
            "altitude",

            "origem_este",
            "origem_norte",
            "origem_tvd",

            "sistema_coordenadas",
            "localizacao",
            "local_sondagem",
            "detalhes",
        ]
        widgets = {
            "projeto": forms.Select(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black"}),
            "nome": forms.TextInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black"}),
            "tipo": forms.Select(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black"}),
            "estado": forms.Select(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black"}),

            "profundidade_inicial": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),
            "profundidade_alvo_inicial": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),
            "profundidade_alvo_atual": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),
            "profundidade_atual": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),
            "profundidade_maxima_atingida": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),

            "inclinacao_planeada_inicial": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),
            "inclinacao_planeada_atual": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),
            "azimute_planeado_inicial": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),
            "azimute_planeado_atual": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),

            "inclinacao_real_atual": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),
            "azimute_real_atual": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),
            "magnetismo": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),

            "latitude": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.000001}),
            "longitude": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.000001}),
            "altitude": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),

            "origem_este": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),
            "origem_norte": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),
            "origem_tvd": forms.NumberInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "step": 0.01}),

            "sistema_coordenadas": forms.Select(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black"}),
            "localizacao": forms.TextInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black"}),
            "local_sondagem": forms.TextInput(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black"}),
            "detalhes": forms.Textarea(attrs={"class": "p-2 rounded border border-gray-400 bg-white text-black", "rows": 3}),
        }

    def _validar_inclinacao(self, valor):
        if valor is not None and not (-90 <= valor <= 90):
            raise forms.ValidationError("A inclinação deve estar entre -90° e 90°.")
        return valor

    def _validar_azimute(self, valor):
        if valor is not None and not (0 <= valor <= 360):
            raise forms.ValidationError("O azimute deve estar entre 0 e 360°.")
        return valor

    def clean_inclinacao_planeada_inicial(self):
        return self._validar_inclinacao(self.cleaned_data.get("inclinacao_planeada_inicial"))

    def clean_inclinacao_planeada_atual(self):
        return self._validar_inclinacao(self.cleaned_data.get("inclinacao_planeada_atual"))

    def clean_inclinacao_real_atual(self):
        return self._validar_inclinacao(self.cleaned_data.get("inclinacao_real_atual"))

    def clean_azimute_planeado_inicial(self):
        return self._validar_azimute(self.cleaned_data.get("azimute_planeado_inicial"))

    def clean_azimute_planeado_atual(self):
        return self._validar_azimute(self.cleaned_data.get("azimute_planeado_atual"))

    def clean_azimute_real_atual(self):
        return self._validar_azimute(self.cleaned_data.get("azimute_real_atual"))

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

    def clean(self):
        cleaned = super().clean()

        pi = cleaned.get("profundidade_inicial")
        pai = cleaned.get("profundidade_alvo_inicial")
        paa = cleaned.get("profundidade_alvo_atual")
        pat = cleaned.get("profundidade_atual")
        pma = cleaned.get("profundidade_maxima_atingida")

        for campo_nome, valor in [
            ("profundidade_inicial", pi),
            ("profundidade_alvo_inicial", pai),
            ("profundidade_alvo_atual", paa),
            ("profundidade_atual", pat),
            ("profundidade_maxima_atingida", pma),
        ]:
            if valor is not None and valor < 0:
                self.add_error(campo_nome, "O valor não pode ser negativo.")

        if pi is not None and pai is not None and pai < pi:
            self.add_error("profundidade_alvo_inicial", "A profundidade alvo inicial não pode ser menor que a profundidade inicial.")

        if pi is not None and paa is not None and paa < pi:
            self.add_error("profundidade_alvo_atual", "A profundidade alvo atual não pode ser menor que a profundidade inicial.")

        if pi is not None and pat is not None and pat < pi:
            self.add_error("profundidade_atual", "A profundidade atual não pode ser menor que a profundidade inicial.")

        if pat is not None and pma is not None and pma < pat:
            self.add_error("profundidade_maxima_atingida", "A profundidade máxima atingida não pode ser menor que a profundidade atual.")

        return cleaned


class FuroCreateForm(forms.ModelForm):
    class Meta:
        model = Furo
        fields = [
            "projeto",
            "tipo",
            "nome",
            "estado",

            "profundidade_inicial",
            "profundidade_alvo_inicial",

            "inclinacao_planeada_inicial",
            "azimute_planeado_inicial",
            "magnetismo",

            "latitude",
            "longitude",
            "altitude",

            "origem_este",
            "origem_norte",
            "origem_tvd",
            "sistema_coordenadas",

            "localizacao",
            "local_sondagem",
            "detalhes",
        ]
        widgets = {
            "projeto": forms.Select(attrs={"class": "form-control"}),
            "tipo": forms.Select(attrs={"class": "form-control"}),
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-control"}),

            "profundidade_inicial": forms.NumberInput(attrs={"class": "form-control", "step": 0.01}),
            "profundidade_alvo_inicial": forms.NumberInput(attrs={"class": "form-control", "step": 0.01}),

            "inclinacao_planeada_inicial": forms.NumberInput(attrs={"class": "form-control", "step": 0.01}),
            "azimute_planeado_inicial": forms.NumberInput(attrs={"class": "form-control", "step": 0.01}),
            "magnetismo": forms.NumberInput(attrs={"class": "form-control", "step": 0.01}),

            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": 0.000001}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": 0.000001}),
            "altitude": forms.NumberInput(attrs={"class": "form-control", "step": 0.01}),

            "origem_este": forms.NumberInput(attrs={"class": "form-control", "step": 0.01}),
            "origem_norte": forms.NumberInput(attrs={"class": "form-control", "step": 0.01}),
            "origem_tvd": forms.NumberInput(attrs={"class": "form-control", "step": 0.01}),
            "sistema_coordenadas": forms.Select(attrs={"class": "form-control"}),

            "localizacao": forms.TextInput(attrs={"class": "form-control"}),
            "local_sondagem": forms.TextInput(attrs={"class": "form-control"}),
            "detalhes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_inclinacao_planeada_inicial(self):
        valor = self.cleaned_data.get("inclinacao_planeada_inicial")
        if valor is not None and not (-90 <= valor <= 90):
            raise forms.ValidationError("A inclinação planeada inicial deve estar entre -90° e 90°.")
        return valor

    def clean_azimute_planeado_inicial(self):
        valor = self.cleaned_data.get("azimute_planeado_inicial")
        if valor is not None and not (0 <= valor <= 360):
            raise forms.ValidationError("O azimute planeado inicial deve estar entre 0 e 360°.")
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

    def clean(self):
        cleaned = super().clean()

        pi = cleaned.get("profundidade_inicial")
        pai = cleaned.get("profundidade_alvo_inicial")

        if pi is not None and pi < 0:
            self.add_error("profundidade_inicial", "A profundidade inicial não pode ser negativa.")

        if pai is not None and pai < 0:
            self.add_error("profundidade_alvo_inicial", "A profundidade alvo inicial não pode ser negativa.")

        if pi is not None and pai is not None and pai < pi:
            self.add_error("profundidade_alvo_inicial", "A profundidade alvo inicial não pode ser menor que a profundidade inicial.")

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)

        instance.profundidade_alvo_atual = instance.profundidade_alvo_inicial
        instance.inclinacao_planeada_atual = instance.inclinacao_planeada_inicial
        instance.azimute_planeado_atual = instance.azimute_planeado_inicial

        if instance.inclinacao_real_atual is None:
            instance.inclinacao_real_atual = instance.inclinacao_planeada_inicial

        if instance.azimute_real_atual is None:
            instance.azimute_real_atual = instance.azimute_planeado_inicial

        if commit:
            instance.save()

        return instance