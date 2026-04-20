# dispositivos/models/leitura_dispositivo.py
import uuid

from django.core.exceptions import ValidationError
from django.db import models


class LeituraDispositivo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sessao = models.ForeignKey(
        "dispositivos.SessaoDispositivo",
        on_delete=models.CASCADE,
        related_name="leituras",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="leituras_dispositivos",
    )

    leitura_bruta = models.ForeignKey(
        "dispositivos.LeituraBrutaDispositivo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leituras_processadas",
    )

    timestamp_device = models.DateTimeField(null=True, blank=True)
    profundidade_m = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    inclinacao_deg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    azimute_deg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    payload_bruto = models.JSONField(default=dict, blank=True)
    payload_texto = models.TextField(blank=True)
    qualidade = models.CharField(max_length=30, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Leitura de Dispositivo"
        verbose_name_plural = "Leituras de Dispositivos"
        ordering = ["-timestamp_device", "-criado_em"]
        indexes = [
            models.Index(fields=["empresa", "criado_em"]),
            models.Index(fields=["sessao", "criado_em"]),
            models.Index(fields=["sessao", "timestamp_device"]),
            models.Index(fields=["sessao", "profundidade_m"]),
        ]

    def __str__(self):
        return f"Leitura {self.id} - sessão {self.sessao_id}"

    def clean(self):
        super().clean()

        if self.sessao and self.empresa_id and self.sessao.empresa_id != self.empresa_id:
            raise ValidationError({
                "empresa": "A empresa da leitura deve ser a mesma da sessão."
            })

        if self.leitura_bruta and self.sessao_id and self.leitura_bruta.sessao_id != self.sessao_id:
            raise ValidationError({
                "leitura_bruta": "A leitura bruta deve pertencer à mesma sessão da leitura processada."
            })

        if self.profundidade_m is not None and self.profundidade_m < 0:
            raise ValidationError({
                "profundidade_m": "A profundidade não pode ser negativa."
            })

        if self.azimute_deg is not None and not (0 <= self.azimute_deg <= 360):
            raise ValidationError({
                "azimute_deg": "O azimute deve estar entre 0 e 360 graus."
            })

        if self.inclinacao_deg is not None and not (-90 <= self.inclinacao_deg <= 90):
            raise ValidationError({
                "inclinacao_deg": "A inclinação deve estar entre -90 e 90 graus."
            })

    def save(self, *args, **kwargs):
        if self.sessao and self.sessao.empresa_id:
            self.empresa_id = self.sessao.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)