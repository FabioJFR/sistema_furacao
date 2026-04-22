import uuid

from django.core.exceptions import ValidationError
from django.db import models


class DroneSF(models.Model):
    STATUS_CHOICES = [
        ("planeamento", "Planeamento"),
        ("montagem", "Montagem"),
        ("teste", "Teste"),
        ("operacional", "Operacional"),
        ("manutencao", "Manutenção"),
        ("inativo", "Inativo"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="drones_sf",
    )
    nome = models.CharField(max_length=140)
    codigo = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planeamento")
    frame_modelo = models.CharField(max_length=120, blank=True)
    controlador_voo = models.CharField(max_length=120, blank=True)
    firmware_voo = models.CharField(max_length=120, blank=True)
    protocolo_telemetria = models.CharField(max_length=80, blank=True, default="MAVLink")
    companion_computer = models.CharField(max_length=120, blank=True)
    autonomia_alvo_min = models.PositiveIntegerField(default=0)
    payload_alvo_kg = models.FloatField(default=0.0)
    peso_estimado_kg = models.FloatField(default=0.0)
    tensao_sistema_v = models.FloatField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    metadados = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome", "criado_em"]
        verbose_name = "Drone S_F"
        verbose_name_plural = "Drones S_F"
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nome"], name="unique_drone_sf_nome_empresa"),
        ]

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        for field_name in ["payload_alvo_kg", "peso_estimado_kg"]:
            valor = getattr(self, field_name, None)
            if valor is not None and valor < 0:
                raise ValidationError({field_name: "O valor não pode ser negativo."})
        if self.tensao_sistema_v is not None and self.tensao_sistema_v < 0:
            raise ValidationError({"tensao_sistema_v": "A tensão do sistema não pode ser negativa."})


class ModuloDroneSF(models.Model):
    TIPO_CHOICES = [
        ("estrutura", "Estrutura"),
        ("propulsao", "Propulsão"),
        ("energia", "Energia"),
        ("controlo_voo", "Controlo de voo"),
        ("computacao", "Computação embarcada"),
        ("camera", "Câmara"),
        ("comunicacao", "Comunicação"),
        ("seguranca", "Segurança"),
        ("outro", "Outro"),
    ]
    STATUS_CHOICES = [
        ("planeado", "Planeado"),
        ("instalado", "Instalado"),
        ("teste", "Em teste"),
        ("ativo", "Ativo"),
        ("avariado", "Avariado"),
        ("substituido", "Substituído"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drone = models.ForeignKey(
        "geologia.DroneSF",
        on_delete=models.CASCADE,
        related_name="modulos",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="modulos_drone_sf",
    )
    nome = models.CharField(max_length=140)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="outro")
    fabricante = models.CharField(max_length=120, blank=True)
    modelo = models.CharField(max_length=120, blank=True)
    numero_serie = models.CharField(max_length=120, blank=True)
    firmware = models.CharField(max_length=120, blank=True)
    peso_kg = models.FloatField(default=0.0)
    consumo_estimado_w = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planeado")
    removivel = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)
    metadados = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipo", "nome"]
        verbose_name = "Módulo do Drone S_F"
        verbose_name_plural = "Módulos do Drone S_F"

    def __str__(self):
        return f"{self.nome} ({self.drone.nome})"

    def clean(self):
        super().clean()
        if self.drone_id and self.empresa_id and self.drone.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa do módulo deve coincidir com a empresa do drone."})
        for field_name in ["peso_kg", "consumo_estimado_w"]:
            valor = getattr(self, field_name, None)
            if valor is not None and valor < 0:
                raise ValidationError({field_name: "O valor não pode ser negativo."})

    def save(self, *args, **kwargs):
        if self.drone_id:
            self.empresa_id = self.drone.empresa_id
        self.full_clean()
        super().save(*args, **kwargs)


class SensorDroneSF(models.Model):
    TIPO_CHOICES = [
        ("proximidade", "Proximidade"),
        ("som", "Som"),
        ("rgb", "RGB"),
        ("termico", "Térmico"),
        ("multiespectral", "Multiespectral"),
        ("lidar", "LiDAR"),
        ("ambiental", "Ambiental"),
        ("geologico", "Geológico"),
        ("outro", "Outro"),
    ]
    STATUS_CHOICES = [
        ("planeado", "Planeado"),
        ("instalado", "Instalado"),
        ("calibracao", "Calibração"),
        ("ativo", "Ativo"),
        ("avariado", "Avariado"),
        ("substituido", "Substituído"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drone = models.ForeignKey(
        "geologia.DroneSF",
        on_delete=models.CASCADE,
        related_name="sensores",
    )
    modulo = models.ForeignKey(
        "geologia.ModuloDroneSF",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sensores",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="sensores_drone_sf",
    )
    nome = models.CharField(max_length=140)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="outro")
    fabricante = models.CharField(max_length=120, blank=True)
    modelo = models.CharField(max_length=120, blank=True)
    interface_ligacao = models.CharField(max_length=80, blank=True)
    alcance_m = models.FloatField(null=True, blank=True)
    taxa_amostragem_hz = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planeado")
    calibrado = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True)
    metadados = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipo", "nome"]
        verbose_name = "Sensor do Drone S_F"
        verbose_name_plural = "Sensores do Drone S_F"

    def __str__(self):
        return f"{self.nome} ({self.drone.nome})"

    def clean(self):
        super().clean()
        if self.drone_id and self.empresa_id and self.drone.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa do sensor deve coincidir com a empresa do drone."})
        if self.modulo_id and self.drone_id and self.modulo.drone_id != self.drone_id:
            raise ValidationError({"modulo": "O módulo selecionado deve pertencer ao mesmo drone."})
        for field_name in ["alcance_m", "taxa_amostragem_hz"]:
            valor = getattr(self, field_name, None)
            if valor is not None and valor < 0:
                raise ValidationError({field_name: "O valor não pode ser negativo."})

    def save(self, *args, **kwargs):
        if self.drone_id:
            self.empresa_id = self.drone.empresa_id
        self.full_clean()
        super().save(*args, **kwargs)


class ConfiguracaoDroneSF(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drone = models.OneToOneField(
        "geologia.DroneSF",
        on_delete=models.CASCADE,
        related_name="configuracao",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="configuracoes_drone_sf",
    )
    telemetria_ativa = models.BooleanField(default=False)
    video_ativo = models.BooleanField(default=False)
    missao_automatica_ativa = models.BooleanField(default=False)
    sensores_proximidade_ativos = models.BooleanField(default=False)
    sensores_som_ativos = models.BooleanField(default=False)
    software_embarcado_ativo = models.BooleanField(default=False)
    endpoint_bridge = models.URLField(blank=True)
    api_key_bridge = models.CharField(max_length=120, blank=True)
    versao_software_embarcado = models.CharField(max_length=120, blank=True)
    observacoes = models.TextField(blank=True)
    metadados = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração do Drone S_F"
        verbose_name_plural = "Configurações do Drone S_F"

    def __str__(self):
        return f"Configuração {self.drone.nome}"

    def clean(self):
        super().clean()
        if self.drone_id and self.empresa_id and self.drone.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa da configuração deve coincidir com a empresa do drone."})
        if self.telemetria_ativa and not self.endpoint_bridge:
            raise ValidationError({"endpoint_bridge": "Define o endpoint da bridge para ativar a telemetria."})

    def save(self, *args, **kwargs):
        if self.drone_id:
            self.empresa_id = self.drone.empresa_id
        self.full_clean()
        super().save(*args, **kwargs)


class OperacaoDroneSFTempoReal(models.Model):
    ESTADO_CHOICES = [
        ("desligado", "Desligado"),
        ("pronto", "Pronto"),
        ("em_voo", "Em voo"),
        ("em_missao", "Em missão"),
        ("manutencao", "Em manutenção"),
        ("erro", "Erro"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drone = models.OneToOneField(
        "geologia.DroneSF",
        on_delete=models.CASCADE,
        related_name="operacao_tempo_real",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="operacoes_drone_sf_tempo_real",
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="desligado")
    bridge_ativa = models.BooleanField(default=False)
    bridge_nome = models.CharField(max_length=120, blank=True, default="Bridge S_F")
    bridge_base_url = models.URLField(blank=True)
    bridge_api_key = models.CharField(max_length=120, blank=True)
    bridge_ultimo_estado = models.CharField(max_length=120, blank=True)
    bridge_ultimo_erro = models.TextField(blank=True)
    live_view_url = models.URLField(blank=True)
    frame_snapshot_url = models.URLField(blank=True)
    latitude_atual = models.FloatField(null=True, blank=True)
    longitude_atual = models.FloatField(null=True, blank=True)
    altitude_atual_m = models.FloatField(null=True, blank=True)
    velocidade_atual_ms = models.FloatField(null=True, blank=True)
    heading_graus = models.FloatField(null=True, blank=True)
    bateria_percent = models.PositiveIntegerField(null=True, blank=True)
    sinal_percent = models.PositiveIntegerField(null=True, blank=True)
    gravacao_ativa = models.BooleanField(default=False)
    alvo_latitude = models.FloatField(null=True, blank=True)
    alvo_longitude = models.FloatField(null=True, blank=True)
    alvo_altitude_m = models.FloatField(default=35.0)
    ultimo_heartbeat = models.DateTimeField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    metadados = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Operação em tempo real do Drone S_F"
        verbose_name_plural = "Operações em tempo real do Drone S_F"
        ordering = ["-atualizado_em", "-criado_em"]

    def __str__(self):
        return f"Operação S_F {self.drone.nome}"

    def clean(self):
        super().clean()
        if self.drone_id and self.empresa_id and self.drone.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa da operação deve coincidir com a empresa do drone."})
        for field_name in ["latitude_atual", "alvo_latitude"]:
            valor = getattr(self, field_name, None)
            if valor is not None and not (-90 <= valor <= 90):
                raise ValidationError({field_name: "Latitude inválida."})
        for field_name in ["longitude_atual", "alvo_longitude"]:
            valor = getattr(self, field_name, None)
            if valor is not None and not (-180 <= valor <= 180):
                raise ValidationError({field_name: "Longitude inválida."})
        for field_name in ["bateria_percent", "sinal_percent"]:
            valor = getattr(self, field_name, None)
            if valor is not None and not (0 <= valor <= 100):
                raise ValidationError({field_name: "O valor deve estar entre 0 e 100."})
        if self.bridge_ativa and not self.bridge_base_url:
            raise ValidationError({"bridge_base_url": "Define o endpoint base da bridge S_F para ativar a integração."})

    def save(self, *args, **kwargs):
        if self.drone_id:
            self.empresa_id = self.drone.empresa_id
        self.full_clean()
        super().save(*args, **kwargs)


class ComandoDroneSFOperacao(models.Model):
    TIPO_CHOICES = [
        ("goto", "Ir para ponto"),
        ("capturar_foto", "Capturar foto"),
        ("iniciar_video", "Iniciar vídeo"),
        ("parar_video", "Parar vídeo"),
        ("pairar", "Pairar"),
        ("rth", "Return to home"),
    ]
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("enviado", "Enviado"),
        ("executado", "Executado"),
        ("erro", "Erro"),
        ("cancelado", "Cancelado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operacao = models.ForeignKey(
        "geologia.OperacaoDroneSFTempoReal",
        on_delete=models.CASCADE,
        related_name="comandos",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="comandos_drone_sf",
    )
    criado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comandos_drone_sf",
    )
    tipo_comando = models.CharField(max_length=30, choices=TIPO_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    latitude_alvo = models.FloatField(null=True, blank=True)
    longitude_alvo = models.FloatField(null=True, blank=True)
    altitude_alvo_m = models.FloatField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    resposta_execucao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Comando do Drone S_F"
        verbose_name_plural = "Comandos do Drone S_F"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_comando_display()} - {self.get_status_display()}"

    def clean(self):
        super().clean()
        if self.operacao_id and self.empresa_id and self.operacao.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa do comando deve ser a mesma da operação."})
        if self.tipo_comando == "goto" and (self.latitude_alvo is None or self.longitude_alvo is None):
            raise ValidationError({"tipo_comando": "O comando 'Ir para ponto' precisa de latitude e longitude alvo."})

    def save(self, *args, **kwargs):
        if self.operacao_id:
            self.empresa_id = self.operacao.empresa_id
        self.full_clean()
        super().save(*args, **kwargs)


class MissaoProgramadaDroneSF(models.Model):
    TIPO_FREQUENCIA_CHOICES = [
        ("diaria", "Diária"),
        ("semanal", "Semanal"),
        ("pontual", "Pontual"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drone = models.ForeignKey("geologia.DroneSF", on_delete=models.CASCADE, related_name="missoes_programadas")
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="missoes_programadas_drone_sf")
    nome = models.CharField(max_length=140)
    ativa = models.BooleanField(default=True)
    tipo_frequencia = models.CharField(max_length=20, choices=TIPO_FREQUENCIA_CHOICES, default="diaria")
    hora_execucao = models.TimeField()
    dia_semana = models.PositiveSmallIntegerField(null=True, blank=True)
    latitude_alvo = models.FloatField()
    longitude_alvo = models.FloatField()
    altitude_alvo_m = models.FloatField(default=35.0)
    gravar_video = models.BooleanField(default=True)
    captar_foto = models.BooleanField(default=False)
    pairar_no_destino = models.BooleanField(default=False)
    regressar_base = models.BooleanField(default=True)
    ativar_sensores = models.BooleanField(default=True)
    usar_live_view = models.BooleanField(default=True)
    notas = models.TextField(blank=True)
    metadados = models.JSONField(default=dict, blank=True)
    ultima_execucao_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Missão programada do Drone S_F"
        verbose_name_plural = "Missões programadas do Drone S_F"
        ordering = ["ativa", "hora_execucao", "nome"]

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        if self.drone_id and self.empresa_id and self.drone.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa da missão deve coincidir com a empresa do drone."})
        if not (-90 <= self.latitude_alvo <= 90):
            raise ValidationError({"latitude_alvo": "Latitude inválida."})
        if not (-180 <= self.longitude_alvo <= 180):
            raise ValidationError({"longitude_alvo": "Longitude inválida."})
        if self.altitude_alvo_m < 0:
            raise ValidationError({"altitude_alvo_m": "A altitude alvo não pode ser negativa."})
        if self.tipo_frequencia == "semanal" and self.dia_semana is None:
            raise ValidationError({"dia_semana": "Define o dia da semana para uma missão semanal."})
        if self.tipo_frequencia != "semanal":
            self.dia_semana = None
        if not any(
            [
                self.gravar_video,
                self.captar_foto,
                self.pairar_no_destino,
                self.regressar_base,
                self.ativar_sensores,
                self.usar_live_view,
            ]
        ):
            raise ValidationError({"nome": "Seleciona pelo menos uma ação para a missão programada."})

    def save(self, *args, **kwargs):
        if self.drone_id:
            self.empresa_id = self.drone.empresa_id
        self.full_clean()
        super().save(*args, **kwargs)
