

from django.core.exceptions import ValidationError
from django.db import models


class LeituraDispositivoMedicaoLink(models.Model):
    leitura = models.OneToOneField(
        "dispositivos.LeituraDispositivo",
        on_delete=models.CASCADE,
        related_name="link_medicao",
    )
    medicao = models.ForeignKey(
        "projetos.Medicao",
        on_delete=models.CASCADE,
        related_name="links_dispositivo",
    )

    class Meta:
        verbose_name = "Ligação Leitura-Medição"
        verbose_name_plural = "Ligações Leitura-Medição"

    def __str__(self):
        return f"{self.leitura_id} -> {self.medicao_id}"

    def clean(self):
        super().clean()

        if self.leitura and self.medicao:
            leitura_empresa_id = getattr(self.leitura, "empresa_id", None)
            medicao_empresa_id = getattr(self.medicao, "empresa_id", None)

            if leitura_empresa_id and medicao_empresa_id and leitura_empresa_id != medicao_empresa_id:
                raise ValidationError({
                    "medicao": "A medição deve pertencer à mesma empresa da leitura."
                })

            leitura_sessao = getattr(self.leitura, "sessao", None)
            leitura_furo_id = getattr(leitura_sessao, "furo_id", None) if leitura_sessao else None
            medicao_furo_id = getattr(self.medicao, "furo_id", None)

            if leitura_furo_id and medicao_furo_id and leitura_furo_id != medicao_furo_id:
                raise ValidationError({
                    "medicao": "A medição deve pertencer ao mesmo furo da leitura."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)