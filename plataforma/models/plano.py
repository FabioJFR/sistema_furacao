# plataforma/models/plano.py
import uuid
from django.db import models


class Plano(models.Model):
    PERIODO_COBRANCA_CHOICES = [
        (1, "1 mês"),
        (3, "3 meses"),
        (6, "6 meses"),
        (12, "12 meses"),
    ]

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
    permite_cobranca_mensal = models.BooleanField(default=True)
    permite_cobranca_anual = models.BooleanField(default=True)
    periodos_cobranca_disponiveis = models.JSONField(default=list, blank=True)

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

    @property
    def periodos_cobranca_disponiveis_normalizados(self):
        periodos = []
        for valor in self.periodos_cobranca_disponiveis or []:
            try:
                inteiro = int(valor)
            except (TypeError, ValueError):
                continue
            if inteiro in [1, 3, 6, 12]:
                periodos.append(inteiro)

        if not periodos:
            if self.permite_cobranca_mensal:
                periodos.append(1)
            if self.permite_cobranca_anual:
                periodos.append(12)

        if not periodos:
            periodos = [1, 12]

        return sorted(set(periodos))

    @property
    def periodos_cobranca_label(self):
        labels = {
            1: "1 mês",
            3: "3 meses",
            6: "6 meses",
            12: "12 meses",
        }
        return ", ".join(labels.get(periodo, f"{periodo} meses") for periodo in self.periodos_cobranca_disponiveis_normalizados)

    def __str__(self):
        return self.nome
