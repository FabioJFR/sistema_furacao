from django.db import models
from django.contrib.auth.models import User

from .empregado import Empregados
from .furo import Furo


class ConfiguracaoPerfuracaoEmpregado(models.Model):
    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name="configuracoes_perfuracao"
    )

    furo = models.ForeignKey(
        Furo,
        on_delete=models.CASCADE,
        related_name="configuracoes_perfuracao"
    )

    # String de perfuração
    comprimento_tubo = models.FloatField(default=3.0)
    comprimento_karoutier = models.FloatField(default=0.0)
    comprimento_acrescento = models.FloatField(default=0.0)
    comprimento_calibrador = models.FloatField(default=0.0)
    comprimento_record = models.FloatField(default=0.0)
    comprimento_bit = models.FloatField(default=0.0)

    # Conjunto interior
    comprimento_caixa_mola = models.FloatField(default=0.0)
    comprimento_tubo_interior = models.FloatField(default=0.0)
    comprimento_cabeca_interior = models.FloatField(default=0.0)

    atualizado_em = models.DateTimeField(auto_now=True)
    atualizado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="configuracoes_perfuracao_atualizadas"
    )

    class Meta:
        unique_together = ("empregado", "furo")
        ordering = ["furo__nome"]
        verbose_name = "Configuração de Perfuração do Empregado"
        verbose_name_plural = "Configurações de Perfuração dos Empregados"

    def __str__(self):
        return f"{self.empregado.nome} - {self.furo.nome}"
    
    