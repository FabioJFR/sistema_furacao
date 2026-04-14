import uuid
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