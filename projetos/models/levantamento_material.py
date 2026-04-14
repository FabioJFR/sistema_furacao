import uuid
from django.db import models
from .material import Material
from .empregado import Empregados
from .projeto import Projeto
from.furo import Furo


##################################
######### LEVANTAMENTO MATERIAL ##
##################################
class LevantamentoMaterial(models.Model):
    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name='levantamentos_materiais'
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='levantamentos'
    )
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='levantamentos_materiais'
    )
    furo = models.ForeignKey(
        Furo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='levantamentos_materiais'
    )

    quantidade = models.IntegerField(default=1)
    data = models.DateField()
    observacoes = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-criado_em']
        verbose_name = "Levantamento de Material"
        verbose_name_plural = "Levantamentos de Materiais"

    def __str__(self):
        return f"{self.empregado.nome} - {self.material.nome} ({self.quantidade})"