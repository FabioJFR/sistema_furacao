import uuid

from django.core.exceptions import ValidationError
from django.db import models


class ImportacaoFuro3DExterna(models.Model):
    ORIGEM_REGISTO_CHOICES = [
        ("externa", "Carregado de outra aplicação"),
        ("interna", "Criado internamente"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="importacoes_furo_3d",
    )
    furo = models.ForeignKey(
        "Furo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="importacoes_externas_3d",
    )
    nome = models.CharField(max_length=200)
    origem_aplicacao = models.CharField(max_length=200, blank=True)
    origem_registo = models.CharField(
        max_length=20,
        choices=ORIGEM_REGISTO_CHOICES,
        default="externa",
    )
    formato_arquivo = models.CharField(max_length=20, blank=True)
    payload_json = models.JSONField(default=dict, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Importação 3D Externa"
        verbose_name_plural = "Importações 3D Externas"

    def __str__(self):
        return self.nome or "Importação 3D"

    def clean(self):
        super().clean()

        if self.furo and self.furo.empresa_id != self.empresa_id:
            raise ValidationError({
                "furo": "O furo selecionado não pertence à mesma empresa da importação."
            })

        if not isinstance(self.payload_json, dict):
            raise ValidationError({
                "payload_json": "O payload da importação deve ser um objeto JSON."
            })
