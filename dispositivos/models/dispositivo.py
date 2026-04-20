import uuid

from django.core.exceptions import ValidationError
from django.db import models


class Dispositivo(models.Model):
    TIPO_CHOICES = [
        ("magcruiser", "MagCruiser"),
    ]

    CANAL_CHOICES = [
        ("usb_serial", "USB / Serial"),
        ("bluetooth", "Bluetooth"),
        ("arquivo", "Arquivo"),
        ("simulador", "Simulador"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="dispositivos",
    )

    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=40, choices=TIPO_CHOICES)
    canal = models.CharField(max_length=40, choices=CANAL_CHOICES)

    identificador_fisico = models.CharField(max_length=120, blank=True)
    porta = models.CharField(max_length=120, blank=True)
    mac_address = models.CharField(max_length=120, blank=True)
    baudrate = models.IntegerField(default=115200)

    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dispositivo"
        verbose_name_plural = "Dispositivos"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    def clean(self):
        super().clean()

        if not self.empresa_id:
            raise ValidationError({
                "empresa": "O dispositivo deve estar associado a uma empresa."
            })

        if self.canal == "usb_serial" and not self.porta:
            raise ValidationError({
                "porta": "Informe a porta para dispositivos USB / Serial."
            })

        if self.canal == "bluetooth" and not self.mac_address:
            raise ValidationError({
                "mac_address": "Informe o endereço Bluetooth para este dispositivo."
            })

        if self.baudrate is not None and self.baudrate <= 0:
            raise ValidationError({
                "baudrate": "O baudrate deve ser maior que zero."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)