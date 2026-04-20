import uuid
from django.db import models


class Empresa(models.Model):
    STATUS_CHOICES = [
        ("ativa", "Ativa"),
        ("teste", "Teste"),
        ("suspensa", "Suspensa"),
        ("cancelada", "Cancelada"),
    ]

    PLANO_CHOICES = [
        ("basic", "Basic"),
        ("pro", "Pro"),
        ("enterprise", "Enterprise"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nome = models.CharField(max_length=200)
    nome_comercial = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True)

    nif = models.CharField(max_length=30, blank=True)
    pais = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    morada = models.CharField(max_length=255, blank=True)

    responsavel_nome = models.CharField(max_length=200, blank=True)
    responsavel_email = models.EmailField(blank=True)
    responsavel_telefone = models.CharField(max_length=30, blank=True)

    plano = models.CharField(max_length=20, choices=PLANO_CHOICES, default="basic")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="teste")

    data_inicio = models.DateField(blank=True, null=True)
    data_fim = models.DateField(blank=True, null=True)

    limite_utilizadores = models.PositiveIntegerField(default=5)
    observacoes = models.TextField(blank=True)

    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.nome