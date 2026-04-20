import uuid
from django.db import models
from django.utils import timezone


class SubscricaoEmpresa(models.Model):
    ESTADO_CHOICES = [
        ("ativa", "Ativa"),
        ("pendente", "Pendente"),
        ("expirada", "Expirada"),
        ("cancelada", "Cancelada"),
        ("suspensa", "Suspensa"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    empresa = models.ForeignKey(
        "Empresa",
        on_delete=models.CASCADE,
        related_name="subscricoes",
    )

    plano = models.ForeignKey(
        "Plano",
        on_delete=models.PROTECT,
        related_name="subscricoes",
    )

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendente")

    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    data_inicio = models.DateField(default=timezone.now)
    data_fim = models.DateField(null=True, blank=True)
    renovacao_automatica = models.BooleanField(default=False)

    observacoes = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.empresa.nome} - {self.plano.nome} ({self.estado})"