import uuid
from django.db import models
from .projeto import Projeto
from .furo import Furo


# ------------------------
# Maquina
# ------------------------
class Maquina(models.Model):
    ESTADO_CHOICES = [
        ('operacional', 'Operacional'),
        ('avariada', 'Avariada'),
        ('reparacao', 'Reparação'),
        ('sucata', 'Sucata'),
        ('parada', 'Parada'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    projetos = models.ManyToManyField(
        Projeto,
        blank=True,
        related_name='maquinas'
    )
    projeto_atual = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maquinas_atuais'
    )

    furos = models.ManyToManyField(
        Furo,
        blank=True,
        related_name='maquinas'
    )

    nome = models.CharField(max_length=200)
    tipo = models.CharField(max_length=100, blank=True)
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, blank=True)

    data_compra = models.DateField(null=True, blank=True)
    data_registo = models.DateField(null=True, blank=True)
    data_revisao = models.DateField(null=True, blank=True)

    matricula = models.CharField(max_length=20, null=True, blank=True)
    seguro = models.CharField(max_length=200, blank=True)
    data_seguro = models.DateField(null=True, blank=True)
    data_iuc = models.DateField(null=True, blank=True)

    km = models.BigIntegerField(default=0, blank=True)
    horimetro = models.FloatField(default=0.0, blank=True)
    ano_registo = models.IntegerField(default=0, blank=True)
    valor = models.FloatField(default=0.0, blank=True)

    localizacao_atual = models.CharField(max_length=200, blank=True)
    observacoes = models.TextField(blank=True)

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='operacional'
    )

    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome
