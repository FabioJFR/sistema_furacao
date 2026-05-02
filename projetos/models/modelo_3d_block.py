import uuid

from django.conf import settings
from django.db import models


class Modelo3DBlock(models.Model):
    FORMATO_CHOICES = [
        ("csv", "CSV"),
        ("json", "JSON"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modelos_block_3d",
    )
    nome = models.CharField(max_length=255)
    formato = models.CharField(max_length=10, choices=FORMATO_CHOICES)
    conteudo_texto = models.TextField(default="", blank=True)
    tamanho_bytes = models.BigIntegerField(default=0)
    resumo_json = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Modelo 3D Block"
        verbose_name_plural = "Modelos 3D Block"

    def __str__(self):
        return f"{self.nome} ({self.formato.upper()})"
