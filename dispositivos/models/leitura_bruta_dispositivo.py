

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class LeituraBrutaDispositivo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sessao = models.ForeignKey(
        "dispositivos.SessaoDispositivo",
        on_delete=models.CASCADE,
        related_name="leituras_brutas",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="leituras_brutas_dispositivos",
    )

    sequencia = models.PositiveIntegerField(default=1)
    payload_texto = models.TextField(blank=True)
    payload_json = models.JSONField(null=True, blank=True)
    payload_hex = models.TextField(blank=True)

    recebido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Leitura Bruta de Dispositivo"
        verbose_name_plural = "Leituras Brutas de Dispositivos"
        ordering = ["-recebido_em"]
        unique_together = [("sessao", "sequencia")]

    def __str__(self):
        return f"Leitura bruta {self.sequencia} - sessão {self.sessao_id}"

    def clean(self):
        super().clean()

        if self.sessao and self.empresa_id and self.sessao.empresa_id != self.empresa_id:
            raise ValidationError({
                "empresa": "A empresa da leitura bruta deve ser a mesma da sessão."
            })

        if self.sequencia is not None and self.sequencia <= 0:
            raise ValidationError({
                "sequencia": "A sequência deve ser maior que zero."
            })

        if not self.payload_texto and not self.payload_json and not self.payload_hex:
            raise ValidationError(
                "A leitura bruta deve conter pelo menos um tipo de payload."
            )

    def save(self, *args, **kwargs):
        if self.sessao and self.sessao.empresa_id:
            self.empresa_id = self.sessao.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)