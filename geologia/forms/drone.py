import json

from django import forms

from geologia.models import DroneComandoOperacao, DroneOperacaoTempoReal, MissaoDroneFuro


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


class MissaoDroneFuroForm(forms.ModelForm):
    def __init__(self, *args, furo=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.furo = furo
        self.empresa = empresa
        if self.furo is not None:
            self.instance.furo = self.furo
        if self.empresa is not None:
            self.instance.empresa_id = _resolver_empresa_id(self.empresa)
        self.fields["metadados_json"] = forms.CharField(
            required=False,
            widget=forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full font-mono", "rows": 8}),
            help_text="Opcional. Cola aqui um JSON exportado do voo para preencher automaticamente os campos da missao.",
            label="Metadados JSON do voo",
        )
        self.fields["ficheiro_metadados"] = forms.FileField(
            required=False,
            widget=forms.FileInput(attrs={"class": "border rounded px-3 py-2 w-full", "accept": ".json,.txt"}),
            help_text="Opcional. Importa um ficheiro JSON/TXT com metadados exportados do voo DJI.",
            label="Ficheiro de metadados do voo",
        )

    class Meta:
        model = MissaoDroneFuro
        fields = [
            "titulo",
            "status",
            "data_voo",
            "piloto_nome",
            "objetivo",
            "tipo_missao",
            "modo_captura",
            "altitude_maxima_m",
            "altitude_rth_m",
            "duracao_minutos",
            "area_coberta_m2",
            "velocidade_max_ms",
            "numero_fotos",
            "numero_videos",
            "bateria_inicio_percent",
            "bateria_fim_percent",
            "firmware",
            "app_origem",
            "ponto_descolagem_lat",
            "ponto_descolagem_lon",
            "latitude_centro",
            "longitude_centro",
            "ortomosaico",
            "modelo_3d",
            "log_voo",
            "relatorio_processamento",
            "observacoes",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "status": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "data_voo": forms.DateInput(attrs={"class": "border rounded px-3 py-2 w-full", "type": "date"}),
            "piloto_nome": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "objetivo": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 3}),
            "tipo_missao": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "modo_captura": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "altitude_maxima_m": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "altitude_rth_m": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "duracao_minutos": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "area_coberta_m2": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "velocidade_max_ms": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "numero_fotos": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "numero_videos": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "bateria_inicio_percent": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "bateria_fim_percent": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "firmware": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "app_origem": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "ponto_descolagem_lat": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "ponto_descolagem_lon": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "latitude_centro": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "longitude_centro": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "ortomosaico": forms.FileInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "modelo_3d": forms.FileInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "log_voo": forms.FileInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "relatorio_processamento": forms.FileInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "observacoes": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 3}),
        }

    def clean_metadados_json(self):
        valor = self.cleaned_data.get("metadados_json")
        if not valor:
            return {}
        try:
            dados = json.loads(valor)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"JSON invalido: {exc.msg}") from exc
        if not isinstance(dados, dict):
            raise forms.ValidationError("Os metadados devem estar em formato de objeto JSON.")
        return dados

    def clean_ficheiro_metadados(self):
        ficheiro = self.cleaned_data.get("ficheiro_metadados")
        if not ficheiro:
            return {}

        try:
            conteudo = ficheiro.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise forms.ValidationError("O ficheiro de metadados deve estar em UTF-8.") from exc

        try:
            dados = json.loads(conteudo)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"Ficheiro JSON invalido: {exc.msg}") from exc

        if not isinstance(dados, dict):
            raise forms.ValidationError("O ficheiro de metadados deve conter um objeto JSON.")

        return dados

    def clean(self):
        cleaned = super().clean()
        if self.furo and self.empresa is not None:
            empresa_id = _resolver_empresa_id(self.empresa)
            if self.furo.empresa_id != empresa_id:
                raise forms.ValidationError("O furo selecionado nao pertence a empresa atual.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.furo is not None:
            instance.furo = self.furo
        if self.empresa is not None:
            instance.empresa_id = _resolver_empresa_id(self.empresa)
        metadados_importados = {
            **(self.cleaned_data.get("ficheiro_metadados") or {}),
            **(self.cleaned_data.get("metadados_json") or {}),
        }
        if metadados_importados:
            instance.aplicar_metadados_importados(metadados_importados)
        if commit:
            instance.save()
        return instance


class DroneOperacaoTempoRealForm(forms.ModelForm):
    class Meta:
        model = DroneOperacaoTempoReal
        fields = [
            "nome_operacao",
            "furo",
            "estado_conexao",
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
            "satelites_gps",
            "gravacao_ativa",
            "alvo_latitude",
            "alvo_longitude",
            "alvo_altitude_m",
            "observacoes",
        ]
        widgets = {
            "nome_operacao": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "furo": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "estado_conexao": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "bridge_ativa": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "bridge_nome": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "bridge_base_url": forms.URLInput(attrs={"class": "border rounded px-3 py-2 w-full", "placeholder": "http://127.0.0.1:8787" }),
            "bridge_api_key": forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full", "placeholder": "chave-secreta-da-bridge" }),
            "live_view_url": forms.URLInput(attrs={"class": "border rounded px-3 py-2 w-full", "placeholder": "https://..." }),
            "frame_snapshot_url": forms.URLInput(attrs={"class": "border rounded px-3 py-2 w-full", "placeholder": "https://..." }),
            "latitude_atual": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "longitude_atual": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "altitude_atual_m": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "velocidade_atual_ms": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "heading_graus": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "bateria_percent": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "sinal_percent": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "satelites_gps": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "gravacao_ativa": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
            "alvo_latitude": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "alvo_longitude": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "alvo_altitude_m": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
            "observacoes": forms.Textarea(attrs={"class": "border rounded px-3 py-2 w-full", "rows": 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa is not None:
            empresa_id = _resolver_empresa_id(empresa)
            self.instance.empresa_id = empresa_id
            self.fields["furo"].queryset = self.fields["furo"].queryset.filter(empresa_id=empresa_id).order_by("projeto__nome", "nome")
        self.fields["bridge_ativa"].help_text = "Ativa a bridge externa para DJI RC 2 e permite receber heartbeat, vídeo e telemetria."
        self.fields["bridge_base_url"].help_text = "Endpoint base da bridge local, por exemplo http://127.0.0.1:8787."
        self.fields["bridge_api_key"].help_text = "Chave usada pela bridge para enviar estado para a plataforma."


class DroneComandoOperacaoForm(forms.ModelForm):
    def __init__(self, *args, operacao=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.operacao = operacao
        self.empresa = empresa
        if operacao is not None:
            self.instance.operacao = operacao
        if empresa is not None:
            self.instance.empresa = empresa

    class Meta:
        model = DroneComandoOperacao
        fields = [
            "tipo_comando",
            "latitude_alvo",
            "longitude_alvo",
            "altitude_alvo_m",
        ]
        widgets = {
            "tipo_comando": forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
            "latitude_alvo": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "longitude_alvo": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.000001}),
            "altitude_alvo_m": forms.NumberInput(attrs={"class": "border rounded px-3 py-2 w-full", "step": 0.01}),
        }
