from django.conf import settings
from django.db import models


class EventoAnalytics(models.Model):
    TIPO_EVENTO_CHOICES = [
        ("create", "Criação"),
        ("update", "Atualização"),
        ("delete", "Eliminação"),
    ]

    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_analytics_projetos",
    )
    actor_username = models.CharField(max_length=150, blank=True)
    actor_tipo = models.CharField(max_length=50, blank=True)

    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="eventos_analytics",
    )
    projeto = models.ForeignKey(
        "Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_analytics",
    )
    furo = models.ForeignKey(
        "Furo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_analytics",
    )
    empregado = models.ForeignKey(
        "Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_analytics",
    )
    material = models.ForeignKey(
        "Material",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_analytics",
    )
    maquina = models.ForeignKey(
        "Maquina",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_analytics",
    )

    tipo_evento = models.CharField(max_length=20, choices=TIPO_EVENTO_CHOICES)
    entidade_tipo = models.CharField(max_length=100)
    entidade_id = models.CharField(max_length=100)
    entidade_label = models.CharField(max_length=255, blank=True)

    snapshot_antes = models.JSONField(default=dict, blank=True)
    snapshot_depois = models.JSONField(default=dict, blank=True)
    metricas = models.JSONField(default=dict, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Evento Analytics"
        verbose_name_plural = "Eventos Analytics"

    def __str__(self):
        return f"{self.entidade_tipo} {self.get_tipo_evento_display()} ({self.entidade_id})"
