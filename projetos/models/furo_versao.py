import uuid

from django.conf import settings
from django.db import models


class FuroVersao(models.Model):
    ORIGEM_CHOICES = [
        ("criado", "Criado"),
        ("atualizado", "Atualizado"),
        ("medicao", "Medição"),
        ("recalculo", "Recalculo"),
        ("migracao", "Migração"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="furos_versoes",
    )
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versoes_furos",
    )
    furo = models.ForeignKey(
        "projetos.Furo",
        on_delete=models.CASCADE,
        related_name="versoes",
    )
    versao_numero = models.PositiveIntegerField()
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default="atualizado")
    hash_estado = models.CharField(max_length=64)
    dados_snapshot = models.JSONField(default=dict, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="furos_versoes_criadas",
    )
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-versao_numero"]
        verbose_name = "Versão de furo"
        verbose_name_plural = "Versões de furo"
        constraints = [
            models.UniqueConstraint(
                fields=["furo", "versao_numero"],
                name="unique_furo_versao_numero",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "furo", "-criado_em"], name="idx_furo_versao_tempo"),
            models.Index(fields=["origem"], name="idx_furo_versao_origem"),
        ]

    def __str__(self):
        return f"{self.furo.nome} v{self.versao_numero}"

