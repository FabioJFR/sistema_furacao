import uuid
from django.core.exceptions import ValidationError
from django.db import models
from .projeto import Projeto
from .furo import Furo
from .empregado import Empregados

# ------------------------
# Material
# ------------------------
class Material(models.Model):
    ESTADO_CHOICES = [
        ('em_estoque', 'Em estoque'),
        ('sem_stock', 'Sem stock'),
        ('recebido', 'Recebido'),
        ('encomendado', 'Encomendado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='materiais'
    )
    furo = models.ForeignKey(
        Furo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='materiais'
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="materiais"
    )

    nome = models.CharField(max_length=200)
    tipo = models.CharField(max_length=100, blank=True)
    marca = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, blank=True)
    stock_minimo = models.IntegerField(default=5)
    quantidade = models.IntegerField(default=0)
    unidade = models.CharField(max_length=50, blank=True, default='un')
    diametro = models.FloatField(default=0.0, blank=True)

    valor = models.FloatField(default=0.0)
    fornecedor = models.CharField(max_length=200, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='em_estoque'
    )

    localizacao = models.CharField(max_length=200, blank=True)
    observacoes = models.TextField(blank=True)

    data_compra = models.DateField(null=True, blank=True)

    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()

        if self.projeto and not self.projeto.empresa_id:
            raise ValidationError({
                "projeto": "O projeto deve estar associado a uma empresa."
            })

        if self.furo and not self.furo.empresa_id:
            raise ValidationError({
                "furo": "O furo deve estar associado a uma empresa."
            })

        if self.projeto and self.furo and self.furo.projeto_id != self.projeto.id:
            raise ValidationError({
                "furo": "O furo selecionado não pertence ao projeto escolhido."
            })

        if self.projeto and self.projeto.empresa_id:
            if self.empresa_id and self.empresa_id != self.projeto.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa do material deve ser a mesma do projeto."
                })

        if self.furo and self.furo.empresa_id:
            if self.empresa_id and self.empresa_id != self.furo.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa do material deve ser a mesma do furo."
                })

        if self.projeto and self.furo:
            if self.projeto.empresa_id and self.furo.empresa_id:
                if self.projeto.empresa_id != self.furo.empresa_id:
                    raise ValidationError({
                        "furo": "O furo e o projeto devem pertencer à mesma empresa."
                    })

        if self.quantidade is not None and self.quantidade < 0:
            raise ValidationError({
                "quantidade": "A quantidade não pode ser negativa."
            })

        if self.stock_minimo is not None and self.stock_minimo < 0:
            raise ValidationError({
                "stock_minimo": "O stock mínimo não pode ser negativo."
            })

        if self.diametro is not None and self.diametro < 0:
            raise ValidationError({
                "diametro": "O diâmetro não pode ser negativo."
            })

        if self.valor is not None and self.valor < 0:
            raise ValidationError({
                "valor": "O valor não pode ser negativo."
            })

    def save(self, *args, **kwargs):
        if self.projeto and self.projeto.empresa_id:
            self.empresa_id = self.projeto.empresa_id
        elif self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)


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
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="levantamentos_materiais"
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

    def clean(self):
        super().clean()

        empregado = self.empregado if self.empregado_id else None
        material = self.material if self.material_id else None

        if empregado and not empregado.empresa_id:
            raise ValidationError({
                "empregado": "O empregado deve estar associado a uma empresa."
            })

        if material and not material.empresa_id:
            raise ValidationError({
                "material": "O material deve estar associado a uma empresa."
            })

        if empregado and empregado.empresa_id:
            if self.empresa_id and self.empresa_id != empregado.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa deve ser a mesma do empregado."
                })

        if material and material.empresa_id:
            if self.empresa_id and self.empresa_id != material.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa deve ser a mesma do material."
                })

        if material and empregado:
            if material.empresa_id != empregado.empresa_id:
                raise ValidationError({
                    "material": "O material não pertence à empresa do empregado."
                })

        if self.projeto and material and material.projeto_id and self.projeto_id != material.projeto_id:
            raise ValidationError({
                "projeto": "O projeto do levantamento deve ser o mesmo do material."
            })

        if self.furo and self.projeto and self.furo.projeto_id != self.projeto_id:
            raise ValidationError({
                "furo": "O furo do levantamento deve pertencer ao projeto do material."
            })

        if self.quantidade is not None and self.quantidade <= 0:
            raise ValidationError({
                "quantidade": "A quantidade levantada deve ser maior do que zero."
            })

    def save(self, *args, **kwargs):
        if self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id
        elif self.material and self.material.empresa_id:
            self.empresa_id = self.material.empresa_id

        if self.material:
            self.projeto = self.material.projeto

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.empregado.nome} - {self.material.nome} ({self.quantidade})"



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
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="devolucoes_materiais"
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

    def clean(self):
        super().clean()

        empregado = self.empregado if self.empregado_id else None
        material = self.material if self.material_id else None

        if empregado and not empregado.empresa_id:
            raise ValidationError({
                "empregado": "O empregado deve estar associado a uma empresa."
            })

        if material and not material.empresa_id:
            raise ValidationError({
                "material": "O material deve estar associado a uma empresa."
            })

        if empregado and empregado.empresa_id:
            if self.empresa_id and self.empresa_id != empregado.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa deve ser a mesma do empregado."
                })

        if material and material.empresa_id:
            if self.empresa_id and self.empresa_id != material.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa deve ser a mesma do material."
                })

        if material and empregado:
            if material.empresa_id != empregado.empresa_id:
                raise ValidationError({
                    "material": "O material não pertence à empresa do empregado."
                })

        if self.projeto and material and material.projeto_id and self.projeto_id != material.projeto_id:
            raise ValidationError({
                "projeto": "O projeto da devolução deve ser o mesmo do material."
            })

        if self.furo and self.projeto and self.furo.projeto_id != self.projeto_id:
            raise ValidationError({
                "furo": "O furo da devolução deve pertencer ao projeto do material."
            })

        if self.quantidade is not None and self.quantidade <= 0:
            raise ValidationError({
                "quantidade": "A quantidade devolvida deve ser maior do que zero."
            })

    def save(self, *args, **kwargs):
        if self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id
        elif self.material and self.material.empresa_id:
            self.empresa_id = self.material.empresa_id

        if self.material:
            self.projeto = self.material.projeto

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.empregado.nome} devolveu {self.quantidade} x {self.material.nome}"
