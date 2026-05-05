import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class LogGeologicoFuro(models.Model):
    STATUS_VALIDACAO_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("rejeitado", "Rejeitado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="logs_geologicos_furo",
    )
    furo = models.ForeignKey(
        "projetos.Furo",
        on_delete=models.CASCADE,
        related_name="logs_geologicos",
    )
    medicao = models.ForeignKey(
        "projetos.Medicao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_geologicos",
    )
    missao_drone = models.ForeignKey(
        "geologia.MissaoDroneFuro",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_geologicos",
    )
    titulo = models.CharField(max_length=150, blank=True)
    data_registo = models.DateField(default=timezone.now)
    intervalo_de = models.FloatField()
    intervalo_ate = models.FloatField()
    recuperacao_testemunho_percent = models.FloatField(null=True, blank=True)
    rqd_percent = models.FloatField(null=True, blank=True)
    litologia_principal = models.CharField(max_length=120)
    litologia_secundaria = models.CharField(max_length=120, blank=True)
    cor = models.CharField(max_length=80, blank=True)
    granulometria = models.CharField(max_length=80, blank=True)
    alteracao = models.CharField(max_length=120, blank=True)
    mineralizacao = models.CharField(max_length=120, blank=True)
    estrutura = models.CharField(max_length=120, blank=True)
    densidade_fraturas = models.CharField(max_length=120, blank=True)
    nivel_agua_m = models.FloatField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    imagem_referencia = models.ImageField(upload_to="geologia/logging/imagens/", blank=True, null=True)
    metadados = models.JSONField(default=dict, blank=True)
    status_validacao = models.CharField(
        max_length=20,
        choices=STATUS_VALIDACAO_CHOICES,
        default="pendente",
    )
    validado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_geologicos_validados",
    )
    validado_em = models.DateTimeField(null=True, blank=True)
    observacao_validacao = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["intervalo_de", "intervalo_ate", "-criado_em"]
        verbose_name = "Log Geologico do Furo"
        verbose_name_plural = "Logs Geologicos do Furo"

    def __str__(self):
        return f"{self.furo.nome} - {self.intervalo_de:.2f}m a {self.intervalo_ate:.2f}m"

    @property
    def comprimento_intervalo(self):
        return round((self.intervalo_ate or 0) - (self.intervalo_de or 0), 2)

    def clean(self):
        super().clean()

        if not self.furo_id:
            raise ValidationError({"furo": "O log geologico deve estar associado a um furo."})

        if self.furo and not self.furo.empresa_id:
            raise ValidationError({"furo": "O furo deve estar associado a uma empresa."})

        if self.empresa_id and self.furo and self.furo.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa do log deve ser a mesma do furo."})

        if self.intervalo_de is None or self.intervalo_de < 0:
            raise ValidationError({"intervalo_de": "O inicio do intervalo nao pode ser negativo."})

        if self.intervalo_ate is None or self.intervalo_ate < 0:
            raise ValidationError({"intervalo_ate": "O fim do intervalo nao pode ser negativo."})

        if self.intervalo_ate < self.intervalo_de:
            raise ValidationError({"intervalo_ate": "O fim do intervalo nao pode ser inferior ao inicio."})

        for field_name in ["recuperacao_testemunho_percent", "rqd_percent"]:
            valor = getattr(self, field_name, None)
            if valor is not None and not (0 <= valor <= 100):
                raise ValidationError({field_name: "O valor deve estar entre 0 e 100."})

        if self.nivel_agua_m is not None and self.nivel_agua_m < 0:
            raise ValidationError({"nivel_agua_m": "O nivel de agua nao pode ser negativo."})

        if self.medicao_id:
            if self.medicao.furo_id != self.furo_id:
                raise ValidationError({"medicao": "A medicao associada deve pertencer ao mesmo furo."})
            if self.empresa_id and self.medicao.empresa_id != self.empresa_id:
                raise ValidationError({"medicao": "A medicao nao pertence a empresa atual."})

        if self.missao_drone_id:
            if self.missao_drone.furo_id != self.furo_id:
                raise ValidationError({"missao_drone": "A missao de drone deve pertencer ao mesmo furo."})
            if self.empresa_id and self.missao_drone.empresa_id != self.empresa_id:
                raise ValidationError({"missao_drone": "A missao de drone nao pertence a empresa atual."})

    def save(self, *args, **kwargs):
        if self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id
        if not self.titulo:
            self.titulo = f"Intervalo {self.intervalo_de:.2f}m - {self.intervalo_ate:.2f}m"
        self.full_clean()
        super().save(*args, **kwargs)


class AnexoLogGeologico(models.Model):
    TIPO_CHOICES = [
        ("foto", "Foto"),
        ("video", "Video"),
        ("documento", "Documento"),
        ("ortomosaico", "Ortomosaico"),
        ("modelo_3d", "Modelo 3D"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="anexos_logs_geologicos",
    )
    log = models.ForeignKey(
        "geologia.LogGeologicoFuro",
        on_delete=models.CASCADE,
        related_name="anexos",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="foto")
    titulo = models.CharField(max_length=150, blank=True)
    ficheiro = models.FileField(upload_to="geologia/logging/anexos/")
    descricao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Anexo do Log Geologico"
        verbose_name_plural = "Anexos dos Logs Geologicos"

    def __str__(self):
        return self.titulo or f"{self.get_tipo_display()} - {self.log}"

    def clean(self):
        super().clean()

        if self.log and self.log.empresa_id:
            if self.empresa_id and self.empresa_id != self.log.empresa_id:
                raise ValidationError({"empresa": "A empresa do anexo deve ser a mesma do log."})

    def save(self, *args, **kwargs):
        if self.log and self.log.empresa_id:
            self.empresa_id = self.log.empresa_id
        if not self.titulo:
            self.titulo = f"{self.get_tipo_display()} - {self.log.intervalo_de:.2f}m"
        self.full_clean()
        super().save(*args, **kwargs)
