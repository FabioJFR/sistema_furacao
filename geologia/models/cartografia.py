import uuid

from django.core.exceptions import ValidationError
from django.db import models

from core.url_security import validate_configured_url


class FonteCartograficaGeologica(models.Model):
    TIPO_SERVICO_CHOICES = [
        ("wms", "WMS"),
        ("tile", "Tile XYZ"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="fontes_cartograficas_geologicas",
    )
    criado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fontes_cartograficas_geologicas_criadas",
    )
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    pais_regiao = models.CharField(max_length=120, blank=True)
    tipo_servico = models.CharField(max_length=10, choices=TIPO_SERVICO_CHOICES, default="wms")
    url_servico = models.URLField()
    layer_names = models.CharField(max_length=255, blank=True)
    attribution = models.CharField(max_length=255, blank=True)
    formato_imagem = models.CharField(max_length=50, blank=True, default="image/png")
    transparencia = models.BooleanField(default=True)
    opacidade = models.FloatField(default=0.75)
    centro_latitude = models.FloatField(null=True, blank=True)
    centro_longitude = models.FloatField(null=True, blank=True)
    zoom_inicial = models.PositiveSmallIntegerField(null=True, blank=True)
    visivel_por_defeito = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=100)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ordem", "nome"]
        verbose_name = "Fonte Cartográfica Geológica"
        verbose_name_plural = "Fontes Cartográficas Geológicas"

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()

        if self.opacidade is None or not (0 <= self.opacidade <= 1):
            raise ValidationError({"opacidade": "A opacidade deve ficar entre 0 e 1."})

        if self.tipo_servico == "wms" and not (self.layer_names or "").strip():
            raise ValidationError({"layer_names": "Indica as layers quando a fonte é WMS."})

        validate_configured_url(
            field_name="url_servico",
            value=self.url_servico,
            require_tile_placeholders=self.tipo_servico == "tile",
        )

        if self.centro_latitude is not None and not (-90 <= self.centro_latitude <= 90):
            raise ValidationError({"centro_latitude": "A latitude deve ficar entre -90 e 90."})

        if self.centro_longitude is not None and not (-180 <= self.centro_longitude <= 180):
            raise ValidationError({"centro_longitude": "A longitude deve ficar entre -180 e 180."})

        if (self.centro_latitude is None) != (self.centro_longitude is None):
            raise ValidationError(
                {
                    "centro_latitude": "Indica latitude e longitude em conjunto.",
                    "centro_longitude": "Indica latitude e longitude em conjunto.",
                }
            )

        if self.zoom_inicial is not None and not (0 <= self.zoom_inicial <= 22):
            raise ValidationError({"zoom_inicial": "O zoom inicial deve ficar entre 0 e 22."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
