import uuid
from django.db import models


class Plano(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    TIPO_CHOICES = [
        ("empresa", "Empresa"),
        ("individual", "Individual"),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="empresa")

    preco_mensal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    preco_anual = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    limite_empregados = models.PositiveIntegerField(default=0)
    limite_projetos = models.PositiveIntegerField(default=0)
    limite_furos = models.PositiveIntegerField(default=0)
    limite_armazenamento_gb = models.PositiveIntegerField(default=5)

    # Permissões / comportamento do plano
    permite_multiplos_utilizadores = models.BooleanField(default=True)
    acesso_dashboard_empresa = models.BooleanField(default=True)
    acesso_painel_empregado = models.BooleanField(default=True)

    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome