import uuid

from django.conf import settings
from django.db import models


class FuroArquivadoPlataforma(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="furos_arquivados_plataforma",
    )
    furo_id_origem = models.UUIDField(db_index=True)
    projeto_id_origem = models.UUIDField(null=True, blank=True, db_index=True)
    nome_furo = models.CharField(max_length=200, blank=True)
    estado_no_arquivo = models.CharField(max_length=30, default="concluido")
    versao_arquivo = models.PositiveIntegerField(default=1)
    terminado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="furos_arquivados_terminados",
    )
    terminado_em = models.DateTimeField(null=True, blank=True)
    dados_snapshot = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Furo arquivado da plataforma"
        verbose_name_plural = "Furos arquivados da plataforma"
        constraints = [
            models.UniqueConstraint(
                fields=["furo_id_origem", "versao_arquivo"],
                name="unique_furo_arquivado_versao",
            )
        ]

    def __str__(self):
        return f"{self.nome_furo or self.furo_id_origem} v{self.versao_arquivo}"
