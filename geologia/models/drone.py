import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class MissaoDroneFuro(models.Model):
    STATUS_CHOICES = [
        ("planeada", "Planeada"),
        ("executada", "Executada"),
        ("importada", "Importada"),
        ("analisada", "Analisada"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="missoes_drone_geologia",
    )
    furo = models.ForeignKey(
        "projetos.Furo",
        on_delete=models.CASCADE,
        related_name="missoes_drone_geologia",
    )
    titulo = models.CharField(max_length=150)
    equipamento = models.CharField(max_length=100, default="DJI Mini 4 Pro")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planeada")
    data_voo = models.DateField(default=timezone.now)
    piloto_nome = models.CharField(max_length=120, blank=True)
    objetivo = models.TextField(blank=True)
    tipo_missao = models.CharField(max_length=80, blank=True)
    modo_captura = models.CharField(max_length=80, blank=True)
    altitude_maxima_m = models.FloatField(default=0.0)
    altitude_rth_m = models.FloatField(null=True, blank=True)
    duracao_minutos = models.PositiveIntegerField(default=0)
    area_coberta_m2 = models.FloatField(null=True, blank=True)
    velocidade_max_ms = models.FloatField(null=True, blank=True)
    numero_fotos = models.PositiveIntegerField(default=0)
    numero_videos = models.PositiveIntegerField(default=0)
    bateria_inicio_percent = models.PositiveIntegerField(null=True, blank=True)
    bateria_fim_percent = models.PositiveIntegerField(null=True, blank=True)
    firmware = models.CharField(max_length=120, blank=True)
    app_origem = models.CharField(max_length=120, blank=True)
    ponto_descolagem_lat = models.FloatField(null=True, blank=True)
    ponto_descolagem_lon = models.FloatField(null=True, blank=True)
    latitude_centro = models.FloatField(null=True, blank=True)
    longitude_centro = models.FloatField(null=True, blank=True)
    ortomosaico = models.FileField(upload_to="geologia/drone/ortomosaicos/", blank=True, null=True)
    modelo_3d = models.FileField(upload_to="geologia/drone/modelos_3d/", blank=True, null=True)
    log_voo = models.FileField(upload_to="geologia/drone/logs/", blank=True, null=True)
    relatorio_processamento = models.FileField(upload_to="geologia/drone/processamento/", blank=True, null=True)
    metadados_voo = models.JSONField(default=dict, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_voo", "-criado_em"]
        verbose_name = "Missao de Drone do Furo"
        verbose_name_plural = "Missoes de Drone dos Furos"

    def __str__(self):
        return f"{self.titulo} - {self.furo.nome}"

    @property
    def tem_produtos_processados(self):
        return bool(self.ortomosaico or self.modelo_3d or self.relatorio_processamento)

    @property
    def resumo_captura(self):
        partes = []
        if self.numero_fotos:
            partes.append(f"{self.numero_fotos} fotos")
        if self.numero_videos:
            partes.append(f"{self.numero_videos} videos")
        if self.duracao_minutos:
            partes.append(f"{self.duracao_minutos} min")
        return " · ".join(partes) or "-"

    def aplicar_metadados_importados(self, metadados: dict):
        if not metadados:
            return

        mapeamento_direto = {
            "titulo": "titulo",
            "tipo_missao": "tipo_missao",
            "modo_captura": "modo_captura",
            "piloto_nome": "piloto_nome",
            "firmware": "firmware",
            "app_origem": "app_origem",
            "duracao_minutos": "duracao_minutos",
            "numero_fotos": "numero_fotos",
            "numero_videos": "numero_videos",
            "altitude_maxima_m": "altitude_maxima_m",
            "altitude_rth_m": "altitude_rth_m",
            "velocidade_max_ms": "velocidade_max_ms",
            "area_coberta_m2": "area_coberta_m2",
            "bateria_inicio_percent": "bateria_inicio_percent",
            "bateria_fim_percent": "bateria_fim_percent",
            "latitude_centro": "latitude_centro",
            "longitude_centro": "longitude_centro",
            "ponto_descolagem_lat": "ponto_descolagem_lat",
            "ponto_descolagem_lon": "ponto_descolagem_lon",
        }

        for origem, destino in mapeamento_direto.items():
            valor = metadados.get(origem)
            if valor not in (None, ""):
                setattr(self, destino, valor)

        if metadados.get("objetivo") and not self.objetivo:
            self.objetivo = metadados["objetivo"]

        self.metadados_voo = {
            **(self.metadados_voo or {}),
            **metadados,
        }

    def clean(self):
        super().clean()

        if not self.furo_id:
            raise ValidationError({"furo": "A missao deve estar associada a um furo."})

        if self.furo and not self.furo.empresa_id:
            raise ValidationError({"furo": "O furo deve estar associado a uma empresa."})

        if self.empresa_id and self.furo and self.furo.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa da missao deve ser a mesma do furo."})

        if self.altitude_maxima_m is not None and self.altitude_maxima_m < 0:
            raise ValidationError({"altitude_maxima_m": "A altitude maxima nao pode ser negativa."})

        if self.altitude_rth_m is not None and self.altitude_rth_m < 0:
            raise ValidationError({"altitude_rth_m": "A altitude RTH nao pode ser negativa."})

        if self.area_coberta_m2 is not None and self.area_coberta_m2 < 0:
            raise ValidationError({"area_coberta_m2": "A area coberta nao pode ser negativa."})

        if self.velocidade_max_ms is not None and self.velocidade_max_ms < 0:
            raise ValidationError({"velocidade_max_ms": "A velocidade maxima nao pode ser negativa."})

        if self.latitude_centro is not None and not (-90 <= self.latitude_centro <= 90):
            raise ValidationError({"latitude_centro": "Latitude invalida."})

        if self.longitude_centro is not None and not (-180 <= self.longitude_centro <= 180):
            raise ValidationError({"longitude_centro": "Longitude invalida."})

        if self.ponto_descolagem_lat is not None and not (-90 <= self.ponto_descolagem_lat <= 90):
            raise ValidationError({"ponto_descolagem_lat": "Latitude do ponto de descolagem invalida."})

        if self.ponto_descolagem_lon is not None and not (-180 <= self.ponto_descolagem_lon <= 180):
            raise ValidationError({"ponto_descolagem_lon": "Longitude do ponto de descolagem invalida."})

        for field_name in ["bateria_inicio_percent", "bateria_fim_percent"]:
            valor = getattr(self, field_name, None)
            if valor is not None and not (0 <= valor <= 100):
                raise ValidationError({field_name: "A bateria deve estar entre 0 e 100."})

        if self.bateria_inicio_percent is not None and self.bateria_fim_percent is not None:
            if self.bateria_fim_percent > self.bateria_inicio_percent:
                raise ValidationError({"bateria_fim_percent": "A bateria final nao pode ser superior a bateria inicial."})

    def save(self, *args, **kwargs):
        if self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id
        self.full_clean()
        super().save(*args, **kwargs)


class DroneOperacaoTempoReal(models.Model):
    ESTADO_CONEXAO_CHOICES = [
        ("desligado", "Desligado"),
        ("procurando", "A procurar"),
        ("pronto", "Pronto"),
        ("em_voo", "Em voo"),
        ("em_missao", "Em missão"),
        ("erro", "Erro"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="operacoes_drone_tempo_real",
    )
    furo = models.ForeignKey(
        "projetos.Furo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operacoes_drone_tempo_real",
    )
    equipamento = models.CharField(max_length=100, default="DJI Mini 4 Pro")
    nome_operacao = models.CharField(max_length=160, default="Centro de controlo DJI")
    estado_conexao = models.CharField(max_length=20, choices=ESTADO_CONEXAO_CHOICES, default="desligado")
    bridge_ativa = models.BooleanField(default=False)
    bridge_nome = models.CharField(max_length=120, blank=True, default="Bridge DJI RC 2")
    bridge_base_url = models.URLField(blank=True)
    bridge_api_key = models.CharField(max_length=120, blank=True)
    bridge_ultimo_estado = models.CharField(max_length=120, blank=True)
    bridge_ultimo_erro = models.TextField(blank=True)
    bridge_ultima_sincronizacao = models.DateTimeField(null=True, blank=True)
    live_view_url = models.URLField(blank=True)
    frame_snapshot_url = models.URLField(blank=True)
    latitude_atual = models.FloatField(null=True, blank=True)
    longitude_atual = models.FloatField(null=True, blank=True)
    altitude_atual_m = models.FloatField(null=True, blank=True)
    velocidade_atual_ms = models.FloatField(null=True, blank=True)
    heading_graus = models.FloatField(null=True, blank=True)
    bateria_percent = models.PositiveIntegerField(null=True, blank=True)
    sinal_percent = models.PositiveIntegerField(null=True, blank=True)
    satelites_gps = models.PositiveIntegerField(null=True, blank=True)
    gravacao_ativa = models.BooleanField(default=False)
    alvo_latitude = models.FloatField(null=True, blank=True)
    alvo_longitude = models.FloatField(null=True, blank=True)
    alvo_altitude_m = models.FloatField(default=35.0)
    ultimo_heartbeat = models.DateTimeField(null=True, blank=True)
    metadados = models.JSONField(default=dict, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-atualizado_em", "-criado_em"]
        verbose_name = "Operação drone em tempo real"
        verbose_name_plural = "Operações drone em tempo real"

    def __str__(self):
        return self.nome_operacao or self.equipamento

    def clean(self):
        super().clean()
        if self.furo and self.furo.empresa_id != self.empresa_id:
            raise ValidationError({"furo": "O furo da operação deve pertencer à mesma empresa."})
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
            raise ValidationError({"bridge_base_url": "Define o endpoint base da bridge para ativar a integração."})


class DroneComandoOperacao(models.Model):
    TIPO_COMANDO_CHOICES = [
        ("goto", "Ir para ponto"),
        ("capturar_foto", "Capturar foto"),
        ("iniciar_video", "Iniciar vídeo"),
        ("parar_video", "Parar vídeo"),
        ("rth", "Return to home"),
        ("pairar", "Pairar"),
        ("sincronizar", "Sincronizar estado"),
    ]

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("enviado", "Enviado"),
        ("executado", "Executado"),
        ("cancelado", "Cancelado"),
        ("erro", "Erro"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operacao = models.ForeignKey(
        DroneOperacaoTempoReal,
        on_delete=models.CASCADE,
        related_name="comandos",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="comandos_drone_operacao",
    )
    criado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comandos_drone_operacao",
    )
    tipo_comando = models.CharField(max_length=30, choices=TIPO_COMANDO_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    latitude_alvo = models.FloatField(null=True, blank=True)
    longitude_alvo = models.FloatField(null=True, blank=True)
    altitude_alvo_m = models.FloatField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    resposta_execucao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Comando do drone"
        verbose_name_plural = "Comandos do drone"

    def __str__(self):
        return f"{self.get_tipo_comando_display()} - {self.get_status_display()}"

    def clean(self):
        super().clean()
        if self.operacao and self.operacao.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa do comando deve ser a mesma da operação."})
        if self.tipo_comando == "goto":
            if self.latitude_alvo is None or self.longitude_alvo is None:
                raise ValidationError({"tipo_comando": "O comando 'Ir para ponto' precisa de latitude e longitude alvo."})

    def save(self, *args, **kwargs):
        if self.operacao and self.operacao.empresa_id:
            self.empresa_id = self.operacao.empresa_id
        self.full_clean()
        super().save(*args, **kwargs)
