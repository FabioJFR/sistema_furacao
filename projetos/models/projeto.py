import uuid
from django.db import models

# ------------------------
# Projeto
# ------------------------
class Projeto(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('pausado', 'Pausado'),
        ('concluido', 'Concluído')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=200)
    cliente = models.CharField(max_length=200, blank=True)

    # 🔥 localização (mantive ambos: cidade + coords)
    cidade = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=100, blank=True)
    localizacao_lat = models.FloatField(null=True, blank=True)
    localizacao_lon = models.FloatField(null=True, blank=True)

    data_inicio = models.DateTimeField(auto_now_add=True)
    data_fim = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    notas = models.TextField(blank=True)

    def __str__(self):
        return self.nome

