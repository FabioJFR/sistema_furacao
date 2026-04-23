import uuid

from django.core.exceptions import ValidationError
from django.db import models


class MovimentoFinanceiroPlataforma(models.Model):
    NATUREZA_FLUXO_CHOICES = [
        ("entrada", "Entrada"),
        ("saida", "Saída"),
    ]

    TIPO_MOVIMENTO_CHOICES = [
        ("cobranca", "Cobrança"),
        ("pagamento", "Pagamento"),
        ("ajuste", "Ajuste"),
        ("reembolso", "Reembolso"),
        ("despesa", "Despesa"),
    ]

    CICLO_COBRANCA_CHOICES = [
        ("1", "1 mês"),
        ("3", "3 meses"),
        ("6", "6 meses"),
        ("12", "12 meses"),
        ("mensal", "Mensal"),
        ("anual", "Anual"),
        ("unico", "Único"),
    ]

    CATEGORIA_CHOICES = [
        ("subscricao", "Subscrição"),
        ("renovacao", "Renovação"),
        ("pagamento_inicial", "Pagamento inicial"),
        ("reembolso", "Reembolso"),
        ("ajuste", "Ajuste"),
        ("despesa_operacional", "Despesa operacional"),
        ("despesa_servidor", "Servidor / alojamento"),
        ("despesa_publicidade_youtube", "Publicidade YouTube"),
        ("despesa_publicidade_facebook", "Publicidade Facebook"),
        ("despesa_publicidade_tiktok", "Publicidade TikTok"),
        ("despesa_dominio", "Domínio / endereço"),
        ("despesa_ssl_https", "SSL / HTTPS"),
        ("despesa_marketing", "Marketing"),
        ("despesa_software", "Software / ferramentas"),
        ("outro", "Outro"),
    ]

    METODO_PAGAMENTO_CHOICES = [
        ("manual", "Manual"),
        ("transferencia", "Transferência"),
        ("referencia", "Referência"),
        ("debito_direto", "Débito direto"),
        ("cartao", "Cartão"),
        ("dinheiro", "Dinheiro"),
        ("outro", "Outro"),
    ]

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
        null=True,
        blank=True,
        related_name="movimentos_financeiros",
    )
    perfil_plataforma = models.ForeignKey(
        "PerfilPlataforma",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="movimentos_financeiros",
    )
    plano = models.ForeignKey(
        "Plano",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimentos_financeiros",
    )
    subscricao = models.ForeignKey(
        "SubscricaoEmpresa",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentos_financeiros",
    )

    tipo_movimento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMENTO_CHOICES,
        default="cobranca",
    )
    natureza_fluxo = models.CharField(
        max_length=20,
        choices=NATUREZA_FLUXO_CHOICES,
        default="entrada",
    )
    ciclo_cobranca = models.CharField(
        max_length=20,
        choices=CICLO_COBRANCA_CHOICES,
        default="unico",
    )
    categoria = models.CharField(
        max_length=30,
        choices=CATEGORIA_CHOICES,
        default="outro",
    )
    metodo_pagamento = models.CharField(
        max_length=20,
        choices=METODO_PAGAMENTO_CHOICES,
        default="manual",
    )
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    valor_bruto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_imposto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_liquido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    moeda = models.CharField(max_length=10, default="EUR")
    descricao = models.CharField(max_length=255, blank=True)
    numero_documento = models.CharField(max_length=100, blank=True)
    entidade_nome = models.CharField(max_length=255, blank=True)

    data_competencia = models.DateField(null=True, blank=True)
    data_vencimento = models.DateField(null=True, blank=True)
    data_pagamento = models.DateField(null=True, blank=True)

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendente")
    referencia = models.CharField(max_length=100, blank=True)
    observacoes = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Movimento Financeiro da Plataforma"
        verbose_name_plural = "Movimentos Financeiros da Plataforma"

    def clean(self):
        super().clean()

        movimento_global_plataforma = (
            self.tipo_movimento == "despesa"
            or self.natureza_fluxo == "saida"
            or str(self.categoria or "").startswith("despesa_")
        )

        if not self.empresa_id and not self.perfil_plataforma_id and not movimento_global_plataforma:
            raise ValidationError(
                "O movimento financeiro deve estar associado a uma empresa ou a um perfil individual."
            )

        if self.empresa_id and self.perfil_plataforma_id:
            raise ValidationError(
                "O movimento financeiro não pode estar associado em simultâneo a empresa e perfil individual."
            )

        if self.valor_bruto == 0 and self.valor:
            self.valor_bruto = self.valor

        valor_liquido_calculado = (self.valor_bruto or 0) - (self.valor_desconto or 0) + (self.valor_imposto or 0)
        if self.valor_liquido == 0 and valor_liquido_calculado:
            self.valor_liquido = valor_liquido_calculado

        if self.valor == 0 and self.valor_liquido:
            self.valor = self.valor_liquido

        if self.tipo_movimento == "reembolso":
            self.natureza_fluxo = "saida"
        elif self.tipo_movimento == "despesa":
            self.natureza_fluxo = "saida"
        elif self.tipo_movimento in ["cobranca", "pagamento", "ajuste"] and not self.natureza_fluxo:
            self.natureza_fluxo = "entrada"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.empresa_id:
            destino = self.empresa.nome
        elif self.perfil_plataforma_id:
            destino = getattr(self.perfil_plataforma.user, "username", "Individual")
        else:
            destino = "Plataforma"
        return f"{destino} - {self.valor} {self.moeda}"
