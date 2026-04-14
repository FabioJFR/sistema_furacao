
import uuid
from django.db import models
from .empregado import Empregados
from .material import Material
from .projeto import Projeto
from .furo import Furo

####################################
##### DEVOLUÇÂO DE MATERIAL ########
####################################
class DevolucaoMaterial(models.Model):
    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name='devolucoes_materiais'
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='devolucoes'
    )
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devolucoes_materiais'
    )
    furo = models.ForeignKey(
        Furo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devolucoes_materiais'
    )

    quantidade = models.IntegerField(default=1)
    data = models.DateField()
    observacoes = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-criado_em']
        verbose_name = "Devolução de Material"
        verbose_name_plural = "Devoluções de Materiais"

    def __str__(self):
        return f"{self.empregado.nome} devolveu {self.quantidade} x {self.material.nome}"