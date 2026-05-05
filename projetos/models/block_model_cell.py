import uuid

from django.db import models


class BlockModelCell(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    block_model = models.ForeignKey(
        "projetos.Modelo3DBlock",
        on_delete=models.CASCADE,
        related_name="celulas",
    )
    x = models.IntegerField(default=0)
    y = models.IntegerField(default=0)
    z = models.IntegerField(default=0)
    centro_x = models.FloatField(default=0.0)
    centro_y = models.FloatField(default=0.0)
    centro_z = models.FloatField(default=0.0)
    litologia = models.CharField(max_length=120, blank=True, default="")
    dureza_media = models.FloatField(null=True, blank=True)
    densidade = models.FloatField(null=True, blank=True)
    teor = models.FloatField(null=True, blank=True)
    distancia_ao_furo = models.FloatField(null=True, blank=True)
    dados_json = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["x", "y", "z"]
        indexes = [
            models.Index(fields=["block_model", "x", "y", "z"]),
            models.Index(fields=["block_model", "litologia"]),
        ]
        verbose_name = "Célula de Block Model"
        verbose_name_plural = "Células de Block Model"

    def __str__(self):
        return f"{self.block_model_id} [{self.x},{self.y},{self.z}]"
