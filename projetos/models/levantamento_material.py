from django.core.exceptions import ValidationError
from django.db import models
from .material import Material
from .empregado import Empregados
from .projeto import Projeto
from .furo import Furo


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
    # TODO futuro:
    # - guardar motivo do levantamento e centro de custo
    # - suportar aprovação/validação de levantamento quando necessário
    # - auditar quem criou/editou/cancelou o movimento
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="levantamentos_materiais"
    )
    quantidade = models.IntegerField(default=1)
    data = models.DateField()
    observacoes = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        # TODO futuro:
        # - avaliar índices por empresa/material/data para acelerar consultas
        # - avaliar política de stock reservado vs stock físico
        ordering = ['-data', '-criado_em']
        verbose_name = "Levantamento de Material"
        verbose_name_plural = "Levantamentos de Materiais"

    def __str__(self):
        return f"{self.empregado.nome} - {self.material.nome} ({self.quantidade})"

    def clean(self):
        super().clean()

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
                    "empresa": "A empresa do levantamento deve ser a mesma do empregado."
                })

            if self.material and self.material.empresa_id and self.empresa_id != self.material.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa do levantamento deve ser a mesma do material."
                })

        if self.projeto and self.material and self.material.projeto_id and self.projeto_id != self.material.projeto_id:
            raise ValidationError({
                "projeto": "O projeto do levantamento deve ser o mesmo do material."
            })

        if self.furo and self.material and self.material.furo_id and self.furo_id != self.material.furo_id:
            raise ValidationError({
                "furo": "O furo do levantamento deve ser o mesmo do material."
            })

        if self.material and not self.material.ativo:
            raise ValidationError({
                "material": "Não é possível levantar um material inativo."
            })

        if self.quantidade is not None and self.quantidade <= 0:
            raise ValidationError({
                "quantidade": "A quantidade levantada deve ser maior do que zero."
            })

        if self.material and self.quantidade is not None:
            if self.material.quantidade is not None and self.quantidade > self.material.quantidade:
                raise ValidationError({
                    "quantidade": "A quantidade levantada não pode ser superior ao stock disponível."
                })

    def save(self, *args, **kwargs):
        if self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id
        elif self.material and self.material.empresa_id:
            self.empresa_id = self.material.empresa_id

        if self.material:
            self.projeto = self.material.projeto
            self.furo = self.material.furo

        # TODO futuro:
        # - descontar stock automaticamente com controlo transacional
        # - gerar número interno do movimento
        # - impedir alteração após fecho/logística se essa regra existir

        self.full_clean()
        super().save(*args, **kwargs)