import uuid

from django.conf import settings
from django.db import models


class Modelo3DWireframe(models.Model):
    FORMATO_CHOICES = [
        ("obj", "OBJ"),
        ("dxf", "DXF"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modelos_wireframe_3d",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="modelos_3d_wireframe",
    )
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="modelos_3d_wireframe",
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
        verbose_name = "Modelo 3D Wireframe"
        verbose_name_plural = "Modelos 3D Wireframe"

    def __str__(self):
        return f"{self.nome} ({self.formato.upper()})"
