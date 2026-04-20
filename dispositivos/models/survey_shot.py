

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class SurveyShot(models.Model):
    ORIGEM_CHOICES = [
        ("magcruiser", "MagCruiser"),
        ("manual", "Manual"),
        ("importacao", "Importação"),
        ("simulador", "Simulador"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sessao = models.ForeignKey(
        "dispositivos.SessaoDispositivo",
        on_delete=models.CASCADE,
        related_name="shots",
    )
    furo = models.ForeignKey(
        "projetos.Furo",
        on_delete=models.CASCADE,
        related_name="survey_shots",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="survey_shots",
    )

    profundidade = models.DecimalField(max_digits=10, decimal_places=2)
    inclinacao = models.DecimalField(max_digits=10, decimal_places=2)
    azimute = models.DecimalField(max_digits=10, decimal_places=2)

    magnetismo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    temperatura = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valido = models.BooleanField(default=True)

    origem = models.CharField(max_length=30, choices=ORIGEM_CHOICES, default="magcruiser")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Survey Shot"
        verbose_name_plural = "Survey Shots"
        ordering = ["-criado_em"]

    def __str__(self):
        nome_furo = self.furo.nome if self.furo else "-"
        return f"{nome_furo} - {self.profundidade}m"

    def clean(self):
        super().clean()

        if self.sessao and self.empresa_id and self.sessao.empresa_id != self.empresa_id:
            raise ValidationError({
                "empresa": "A empresa do survey shot deve ser a mesma da sessão."
            })

        if self.furo and self.empresa_id and self.furo.empresa_id != self.empresa_id:
            raise ValidationError({
                "empresa": "A empresa do survey shot deve ser a mesma do furo."
            })

        if self.sessao and self.furo_id:
            sessao_furo_id = getattr(self.sessao, "furo_id", None)
            if sessao_furo_id and sessao_furo_id != self.furo_id:
                raise ValidationError({
                    "furo": "O furo do survey shot deve ser o mesmo da sessão."
                })

        if self.profundidade is not None and self.profundidade < 0:
            raise ValidationError({
                "profundidade": "A profundidade não pode ser negativa."
            })

        if self.azimute is not None and (self.azimute < 0 or self.azimute > 360):
            raise ValidationError({
                "azimute": "O azimute deve estar entre 0 e 360 graus."
            })

        if self.inclinacao is not None and (self.inclinacao < -90 or self.inclinacao > 90):
            raise ValidationError({
                "inclinacao": "A inclinação deve estar entre -90 e 90 graus."
            })

    def save(self, *args, **kwargs):
        if self.sessao and self.sessao.empresa_id:
            self.empresa_id = self.sessao.empresa_id
        elif self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)