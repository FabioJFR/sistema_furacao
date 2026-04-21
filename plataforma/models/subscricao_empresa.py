import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone


class SubscricaoEmpresa(models.Model):
    CICLO_COBRANCA_CHOICES = [
        ("1", "1 mês"),
        ("3", "3 meses"),
        ("6", "6 meses"),
        ("12", "12 meses"),
        ("mensal", "Mensal"),
        ("anual", "Anual"),
    ]

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
    ciclo_cobranca = models.CharField(
        max_length=20,
        choices=CICLO_COBRANCA_CHOICES,
        default="mensal",
    )

    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    data_inicio = models.DateField(default=timezone.now)
    data_fim = models.DateField(null=True, blank=True)
    proxima_renovacao = models.DateField(null=True, blank=True)
    renovacao_definida_manualmente = models.BooleanField(default=False)
    renovacao_automatica = models.BooleanField(default=False)

    observacoes = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.empresa.nome} - {self.plano.nome} ({self.estado})"

    @property
    def periodo_cobranca_meses(self):
        valor = str(self.ciclo_cobranca or "").strip()
        if valor == "mensal":
            return 1
        if valor == "anual":
            return 12
        try:
            inteiro = int(valor)
        except (TypeError, ValueError):
            return 1
        return inteiro if inteiro in [1, 3, 6, 12] else 1

    @property
    def periodo_cobranca_label(self):
        meses = self.periodo_cobranca_meses
        return f"{meses} mês" if meses == 1 else f"{meses} meses"

    @property
    def precisa_renovacao(self):
        if not self.proxima_renovacao:
            return False
        return self.proxima_renovacao <= timezone.now().date()

    @property
    def renovacao_proxima(self):
        if not self.proxima_renovacao:
            return False
        hoje = timezone.now().date()
        return hoje <= self.proxima_renovacao <= (hoje + timedelta(days=7))
