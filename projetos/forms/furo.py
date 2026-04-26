from django import forms

from ..models.furo import Furo
from ..selectors.forms import listar_projetos_empresa_qs, resolver_empresa_id


def _resolver_empresa_id(empresa):
    return resolver_empresa_id(empresa)


def _atribuir_empresa_furo(instance, empresa=None):
    if empresa is not None:
        instance.empresa_id = _resolver_empresa_id(empresa)
    return instance


def _obter_queryset_projetos_empresa(empresa=None):
    return listar_projetos_empresa_qs(empresa)


def _validar_inclinacao(valor, mensagem=None):
    if valor is not None and not (-90 <= valor <= 90):
        raise forms.ValidationError(mensagem or "A inclinação deve estar entre -90° e 90°.")
    return valor


def _validar_azimute(valor, mensagem=None):
    if valor is not None and not (0 <= valor <= 360):
        raise forms.ValidationError(mensagem or "O azimute deve estar entre 0 e 360°.")
    return valor


def _validar_latitude(valor):
    if valor is not None and not (-90 <= valor <= 90):
        raise forms.ValidationError("Latitude deve estar entre -90 e 90.")
    return valor


def _validar_longitude(valor):
    if valor is not None and not (-180 <= valor <= 180):
        raise forms.ValidationError("Longitude deve estar entre -180 e 180.")
    return valor


def _adicionar_erro_valor_negativo(form, campo_nome, valor, mensagem="O valor não pode ser negativo."):
    if valor is not None and valor < 0:
        form.add_error(campo_nome, mensagem)


def _validar_inclinacao_por_tipo(form, cleaned_data):
    tipo = (cleaned_data.get("tipo") or "").strip().lower()
    if tipo != "superficie":
        return

    regras = [
        ("inclinacao_planeada_inicial", "Para furos de Superfície, a inclinação não pode ser positiva."),
        ("inclinacao_planeada_atual", "Para furos de Superfície, a inclinação não pode ser positiva."),
        ("inclinacao_real_atual", "Para furos de Superfície, a inclinação não pode ser positiva."),
    ]
    for campo, mensagem in regras:
        if campo not in cleaned_data:
            continue
        valor = cleaned_data.get(campo)
        if valor is not None and valor > 0:
            form.add_error(campo, mensagem)


class BaseFuroForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa

        _atribuir_empresa_furo(self.instance, empresa=self.empresa)
        self.fields["projeto"].queryset = _obter_queryset_projetos_empresa(self.empresa)

    def _validar_empresa_projeto(self, projeto):
        empresa_id = _resolver_empresa_id(self.empresa) if self.empresa is not None else None

        if self.instance and self.instance.pk and empresa_id is not None:
            if self.instance.empresa_id and self.instance.empresa_id != empresa_id:
                raise forms.ValidationError("Este furo não pertence à empresa atual.")

        if empresa_id is not None and projeto and projeto.empresa_id != empresa_id:
            self.add_error("projeto", "O projeto selecionado não pertence à empresa atual.")

    def clean_latitude(self):
        return _validar_latitude(self.cleaned_data.get("latitude"))

    def clean_longitude(self):
        return _validar_longitude(self.cleaned_data.get("longitude"))


class FuroForm(BaseFuroForm):
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

    def clean_inclinacao_planeada_inicial(self):
        return _validar_inclinacao(self.cleaned_data.get("inclinacao_planeada_inicial"))

    def clean_inclinacao_planeada_atual(self):
        return _validar_inclinacao(self.cleaned_data.get("inclinacao_planeada_atual"))

    def clean_inclinacao_real_atual(self):
        return _validar_inclinacao(self.cleaned_data.get("inclinacao_real_atual"))

    def clean_azimute_planeado_inicial(self):
        return _validar_azimute(self.cleaned_data.get("azimute_planeado_inicial"))

    def clean_azimute_planeado_atual(self):
        return _validar_azimute(self.cleaned_data.get("azimute_planeado_atual"))

    def clean_azimute_real_atual(self):
        return _validar_azimute(self.cleaned_data.get("azimute_real_atual"))

    def clean(self):
        cleaned = super().clean()
        projeto = cleaned.get("projeto")
        self._validar_empresa_projeto(projeto)
        _validar_inclinacao_por_tipo(self, cleaned)

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
            _adicionar_erro_valor_negativo(self, campo_nome, valor)

        if pi is not None and pai is not None and pai < pi:
            self.add_error("profundidade_alvo_inicial", "A profundidade alvo inicial não pode ser menor que a profundidade inicial.")

        if pi is not None and paa is not None and paa < pi:
            self.add_error("profundidade_alvo_atual", "A profundidade alvo atual não pode ser menor que a profundidade inicial.")

        if pi is not None and pat is not None and pat < pi:
            self.add_error("profundidade_atual", "A profundidade atual não pode ser menor que a profundidade inicial.")

        if pat is not None and pma is not None and pma < pat:
            self.add_error("profundidade_maxima_atingida", "A profundidade máxima atingida não pode ser menor que a profundidade atual.")

        return cleaned


class FuroCreateForm(BaseFuroForm):
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
        return _validar_inclinacao(
            self.cleaned_data.get("inclinacao_planeada_inicial"),
            "A inclinação planeada inicial deve estar entre -90° e 90°.",
        )

    def clean_azimute_planeado_inicial(self):
        return _validar_azimute(
            self.cleaned_data.get("azimute_planeado_inicial"),
            "O azimute planeado inicial deve estar entre 0 e 360°.",
        )

    def clean(self):
        cleaned = super().clean()
        projeto = cleaned.get("projeto")
        self._validar_empresa_projeto(projeto)
        _validar_inclinacao_por_tipo(self, cleaned)

        pi = cleaned.get("profundidade_inicial")
        pai = cleaned.get("profundidade_alvo_inicial")

        _adicionar_erro_valor_negativo(
            self,
            "profundidade_inicial",
            pi,
            "A profundidade inicial não pode ser negativa.",
        )
        _adicionar_erro_valor_negativo(
            self,
            "profundidade_alvo_inicial",
            pai,
            "A profundidade alvo inicial não pode ser negativa.",
        )

        if pi is not None and pai is not None and pai < pi:
            self.add_error("profundidade_alvo_inicial", "A profundidade alvo inicial não pode ser menor que a profundidade inicial.")

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        _atribuir_empresa_furo(instance, empresa=self.empresa)

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
