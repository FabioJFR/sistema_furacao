from django.core.exceptions import ValidationError
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
    # TODO futuro:
    # - suportar aprovação/validação de devolução
    # - auditar quem criou/editou/cancelou a devolução
    # - ligação a fluxo de stock (entrada/ajuste)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="devolucoes_materiais"
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
        # TODO futuro:
        # - índices por empresa/material/data para performance
        # - política de bloqueio após fecho/logística
        ordering = ['-data', '-criado_em']
        verbose_name = "Devolução de Material"
        verbose_name_plural = "Devoluções de Materiais"

    def __str__(self):
        nome_empregado = self.empregado.nome if self.empregado_id and self.empregado else "-"
        nome_material = self.material.nome if self.material_id and self.material else "-"
        return f"{nome_empregado} devolveu {self.quantidade} x {nome_material}"

    def clean(self):
        super().clean()

        # Coerência multiempresa
        if self.empregado and not self.empregado.empresa_id:
            raise ValidationError({
                "empregado": "O empregado deve estar associado a uma empresa."
            })

        if self.material and not self.material.empresa_id:
            raise ValidationError({
                "material": "O material deve estar associado a uma empresa."
            })

        if self.empregado and self.material:
            if self.empregado.empresa_id and self.material.empresa_id:
                if self.empregado.empresa_id != self.material.empresa_id:
                    raise ValidationError({
                        "material": "O empregado e o material devem pertencer à mesma empresa."
                    })

        if self.empresa_id:
            if self.empregado and self.empregado.empresa_id and self.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa da devolução deve ser a mesma do empregado."
                })

            if self.material and self.material.empresa_id and self.empresa_id != self.material.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa da devolução deve ser a mesma do material."
                })

        # Coerência com projeto/furo do material
        if self.projeto and self.material and self.material.projeto_id and self.projeto_id != self.material.projeto_id:
            raise ValidationError({
                "projeto": "O projeto da devolução deve ser o mesmo do material."
            })

        if self.furo and self.material and self.material.furo_id and self.furo_id != self.material.furo_id:
            raise ValidationError({
                "furo": "O furo da devolução deve ser o mesmo do material."
            })

        if self.material and not self.material.ativo:
            raise ValidationError({
                "material": "Não é possível devolver um material inativo."
            })

        if self.quantidade is not None and self.quantidade <= 0:
            raise ValidationError({
                "quantidade": "A quantidade devolvida deve ser maior do que zero."
            })

    def save(self, *args, **kwargs):
        # Herdar empresa
        if self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id
        elif self.material and self.material.empresa_id:
            self.empresa_id = self.material.empresa_id

        # Herdar contexto do material
        if self.material:
            self.projeto = self.material.projeto
            self.furo = self.material.furo

        # TODO futuro:
        # - atualizar stock (entrada) com controlo transacional
        # - gerar número interno do movimento
        # - impedir alteração após fecho/logística

        self.full_clean()
        super().save(*args, **kwargs)