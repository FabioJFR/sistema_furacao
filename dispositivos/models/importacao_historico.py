import uuid

from django.db import models


class ImportacaoDispositivoHistorico(models.Model):
    MODO_CHOICES = [
        ("all_existing", "Todas (furos existentes)"),
        ("latest_existing", "Última por furo (furos existentes)"),
        ("all_create_missing", "Todas + criar furos em falta"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="historico_importacoes_dispositivo",
    )
    sessao = models.ForeignKey(
        "dispositivos.SessaoDispositivo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historico_importacoes",
    )
    utilizador = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historico_importacoes_dispositivo",
    )

    nome_ficheiro = models.CharField(max_length=255)
    formato = models.CharField(max_length=20, blank=True)
    modo_aplicacao = models.CharField(max_length=30, choices=MODO_CHOICES, default="all_existing")

    total_linhas = models.PositiveIntegerField(default=0)
    total_gravadas = models.PositiveIntegerField(default=0)
    total_ignoradas = models.PositiveIntegerField(default=0)
    furos_criados = models.PositiveIntegerField(default=0)

    furos_sem_match = models.JSONField(default=list, blank=True)
    resumo_por_furo = models.JSONField(default=dict, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico de Importação de Dispositivo"
        verbose_name_plural = "Históricos de Importação de Dispositivo"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["empresa", "criado_em"]),
            models.Index(fields=["sessao", "criado_em"]),
        ]

    def __str__(self):
        return f"{self.nome_ficheiro} ({self.total_gravadas}/{self.total_linhas})"
