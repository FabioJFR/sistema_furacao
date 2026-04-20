import uuid
from django.db import models


class PagamentoEmpresa(models.Model):
    ESTADO_CHOICES = [
        ("pendente", "Pendente"),
        ("pago", "Pago"),
        ("atrasado", "Atrasado"),
        ("cancelado", "Cancelado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    empresa = models.ForeignKey(
        "Empresa",
        on_delete=models.CASCADE,
        related_name="pagamentos",
    )
    subscricao = models.ForeignKey(
        "SubscricaoEmpresa",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagamentos",
    )

    descricao = models.CharField(max_length=255, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    data_vencimento = models.DateField(null=True, blank=True)
    data_pagamento = models.DateField(null=True, blank=True)

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendente")
    referencia = models.CharField(max_length=100, blank=True)
    observacoes = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.empresa.nome} - {self.valor}€"