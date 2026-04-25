from django import forms

from geologia.models import (
    ComandoDroneSFOperacao,
    ConfiguracaoDroneSF,
    DroneSF,
    MissaoProgramadaDroneSF,
    ModuloDroneSF,
    OperacaoDroneSFTempoReal,
    SensorDroneSF,
)
from geologia.selectors.forms import listar_modulos_sensor_form_qs


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


class DroneSFForm(forms.ModelForm):
    class Meta:
        model = DroneSF
        fields = [
            "nome",
            "codigo",
            "status",
            "frame_modelo",
            "controlador_voo",
            "firmware_voo",
            "protocolo_telemetria",
            "companion_computer",
            "autonomia_alvo_min",
            "payload_alvo_kg",
            "peso_estimado_kg",
            "tensao_sistema_v",
            "observacoes",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "codigo": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "status": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "frame_modelo": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "controlador_voo": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "firmware_voo": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "protocolo_telemetria": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "companion_computer": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "autonomia_alvo_min": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "payload_alvo_kg": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "peso_estimado_kg": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "tensao_sistema_v": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "observacoes": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 4}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa is not None:
            self.instance.empresa_id = _resolver_empresa_id(empresa)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.empresa is not None:
            instance.empresa_id = _resolver_empresa_id(self.empresa)
        if commit:
            instance.save()
        return instance


class ConfiguracaoDroneSFForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoDroneSF
        fields = [
            "telemetria_ativa",
            "video_ativo",
            "missao_automatica_ativa",
            "sensores_proximidade_ativos",
            "sensores_som_ativos",
            "software_embarcado_ativo",
            "endpoint_bridge",
            "api_key_bridge",
            "versao_software_embarcado",
            "observacoes",
        ]
        widgets = {
            "telemetria_ativa": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "video_ativo": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "missao_automatica_ativa": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "sensores_proximidade_ativos": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "sensores_som_ativos": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "software_embarcado_ativo": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "endpoint_bridge": forms.URLInput(attrs={"class": "border rounded px-3 py-2 w-full", "placeholder": "http://127.0.0.1:8787"}),
            "api_key_bridge": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "versao_software_embarcado": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "observacoes": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 4}),
        }

    def __init__(self, *args, drone=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.drone = drone
        self.empresa = empresa
        if drone is not None:
            self.instance.drone = drone
        if empresa is not None:
            self.instance.empresa_id = _resolver_empresa_id(empresa)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.drone is not None:
            instance.drone = self.drone
        if self.empresa is not None:
            instance.empresa_id = _resolver_empresa_id(self.empresa)
        if commit:
            instance.save()
        return instance


class ModuloDroneSFForm(forms.ModelForm):
    class Meta:
        model = ModuloDroneSF
        fields = [
            "nome",
            "tipo",
            "fabricante",
            "modelo",
            "numero_serie",
            "firmware",
            "peso_kg",
            "consumo_estimado_w",
            "status",
            "removivel",
            "observacoes",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "tipo": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "fabricante": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "modelo": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "numero_serie": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "firmware": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "peso_kg": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "consumo_estimado_w": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "status": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "removivel": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "observacoes": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 4}),
        }

    def __init__(self, *args, drone=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.drone = drone
        self.empresa = empresa
        if drone is not None:
            self.instance.drone = drone
        if empresa is not None:
            self.instance.empresa_id = _resolver_empresa_id(empresa)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.drone is not None:
            instance.drone = self.drone
        if self.empresa is not None:
            instance.empresa_id = _resolver_empresa_id(self.empresa)
        if commit:
            instance.save()
        return instance


class SensorDroneSFForm(forms.ModelForm):
    class Meta:
        model = SensorDroneSF
        fields = [
            "modulo",
            "nome",
            "tipo",
            "fabricante",
            "modelo",
            "interface_ligacao",
            "alcance_m",
            "taxa_amostragem_hz",
            "status",
            "calibrado",
            "observacoes",
        ]
        widgets = {
            "modulo": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "nome": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "tipo": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "fabricante": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "modelo": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "interface_ligacao": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "alcance_m": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "taxa_amostragem_hz": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "status": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "calibrado": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "observacoes": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 4}),
        }

    def __init__(self, *args, drone=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.drone = drone
        self.empresa = empresa
        if drone is not None:
            self.instance.drone = drone
            self.fields["modulo"].queryset = drone.modulos.all().order_by("tipo", "nome")
        else:
            self.fields["modulo"].queryset = listar_modulos_sensor_form_qs(None)
        if empresa is not None:
            self.instance.empresa_id = _resolver_empresa_id(empresa)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.drone is not None:
            instance.drone = self.drone
        if self.empresa is not None:
            instance.empresa_id = _resolver_empresa_id(self.empresa)
        if commit:
            instance.save()
        return instance


class OperacaoDroneSFTempoRealForm(forms.ModelForm):
    class Meta:
        model = OperacaoDroneSFTempoReal
        fields = [
            "estado",
            "bridge_ativa",
            "bridge_nome",
            "bridge_base_url",
            "bridge_api_key",
            "live_view_url",
            "frame_snapshot_url",
            "latitude_atual",
            "longitude_atual",
            "altitude_atual_m",
            "velocidade_atual_ms",
            "heading_graus",
            "bateria_percent",
            "sinal_percent",
            "gravacao_ativa",
            "alvo_latitude",
            "alvo_longitude",
            "alvo_altitude_m",
            "observacoes",
        ]
        widgets = {
            "estado": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "bridge_ativa": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "bridge_nome": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "bridge_base_url": forms.URLInput(attrs={"class": "border rounded px-3 py-2 w-full", "placeholder": "http://127.0.0.1:8890"}),
            "bridge_api_key": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "live_view_url": forms.URLInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "frame_snapshot_url": forms.URLInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "latitude_atual": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.000001"}),
            "longitude_atual": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.000001"}),
            "altitude_atual_m": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "velocidade_atual_ms": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "heading_graus": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "bateria_percent": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "sinal_percent": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "gravacao_ativa": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "alvo_latitude": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.000001"}),
            "alvo_longitude": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.000001"}),
            "alvo_altitude_m": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "observacoes": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 4}),
        }

    def __init__(self, *args, drone=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.drone = drone
        self.empresa = empresa
        if drone is not None:
            self.instance.drone = drone
        if empresa is not None:
            self.instance.empresa_id = _resolver_empresa_id(empresa)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.drone is not None:
            instance.drone = self.drone
        if self.empresa is not None:
            instance.empresa_id = _resolver_empresa_id(self.empresa)
        if commit:
            instance.save()
        return instance


class ComandoDroneSFOperacaoForm(forms.ModelForm):
    class Meta:
        model = ComandoDroneSFOperacao
        fields = [
            "tipo_comando",
            "latitude_alvo",
            "longitude_alvo",
            "altitude_alvo_m",
        ]
        widgets = {
            "tipo_comando": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "latitude_alvo": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.000001"}),
            "longitude_alvo": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.000001"}),
            "altitude_alvo_m": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
        }

    def __init__(self, *args, operacao=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.operacao = operacao
        self.empresa = empresa
        if operacao is not None:
            self.instance.operacao = operacao
        if empresa is not None:
            self.instance.empresa = empresa

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.operacao is not None:
            instance.operacao = self.operacao
        if self.empresa is not None:
            instance.empresa = self.empresa
        if commit:
            instance.save()
        return instance


class MissaoProgramadaDroneSFForm(forms.ModelForm):
    class Meta:
        model = MissaoProgramadaDroneSF
        fields = [
            "nome",
            "ativa",
            "tipo_frequencia",
            "hora_execucao",
            "dia_semana",
            "latitude_alvo",
            "longitude_alvo",
            "altitude_alvo_m",
            "gravar_video",
            "captar_foto",
            "pairar_no_destino",
            "regressar_base",
            "ativar_sensores",
            "usar_live_view",
            "notas",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "ativa": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "tipo_frequencia": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "hora_execucao": forms.TimeInput(attrs={"class": "border rounded px-3 py-2 w-full", "type": "time"}),
            "dia_semana": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "min": "0", "max": "6"}),
            "latitude_alvo": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.000001"}),
            "longitude_alvo": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.000001"}),
            "altitude_alvo_m": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": "0.01"}),
            "gravar_video": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "captar_foto": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "pairar_no_destino": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "regressar_base": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "ativar_sensores": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "usar_live_view": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "notas": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 3}),
        }

    def __init__(self, *args, drone=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.drone = drone
        self.empresa = empresa
        if drone is not None:
            self.instance.drone = drone
        if empresa is not None:
            self.instance.empresa = empresa

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.drone is not None:
            instance.drone = self.drone
        if self.empresa is not None:
            instance.empresa = self.empresa
        if commit:
            instance.save()
        return instance
