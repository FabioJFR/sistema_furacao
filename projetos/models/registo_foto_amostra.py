from django.db import models
from .registo import RegistoDiarioEmpregado


class RegistoDiarioFotoAmostra(models.Model):
    registo = models.ForeignKey(
        RegistoDiarioEmpregado,
        on_delete=models.CASCADE,
        related_name="fotos_amostra"
    )
    imagem = models.ImageField(upload_to="registos/amostras/")
    descricao = models.CharField(max_length=200, blank=True, null=True)
    data_upload = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Foto de Amostra do Registo"
        verbose_name_plural = "Fotos de Amostra do Registo"
        ordering = ["-data_upload"]

    def __str__(self):
        return f"Foto amostra - Registo {self.registo.id}"