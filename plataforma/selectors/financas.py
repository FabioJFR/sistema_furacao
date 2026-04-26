from decimal import Decimal

from django.db.models import Q, Sum

from plataforma.models import ConfiguracaoPagamentoPlataforma, MovimentoFinanceiroPlataforma


NATUREZA_ENTRADA = "entrada"
NATUREZA_SAIDA = "saida"


def listar_movimentos_financeiros(*, natureza_fluxo=None):
    queryset = (
        MovimentoFinanceiroPlataforma.objects
        .select_related("empresa", "perfil_plataforma__user", "plano", "subscricao")
        .order_by("-data_vencimento", "-criado_em")
    )
    if natureza_fluxo:
        queryset = queryset.filter(natureza_fluxo=natureza_fluxo)
    return queryset


def obter_movimento_saida_por_pk(pk):
    return MovimentoFinanceiroPlataforma.objects.filter(
        natureza_fluxo=NATUREZA_SAIDA,
        pk=pk,
    ).first()


def somar_valor(queryset, filtro=None):
    aggregate_kwargs = {}
    if filtro is not None:
        aggregate_kwargs["filter"] = filtro
    total = queryset.aggregate(total=Sum("valor", **aggregate_kwargs))["total"]
    return total or Decimal("0.00")


def destino_movimento_label(movimento):
    if movimento.empresa_id:
        return movimento.empresa.nome
    if movimento.perfil_plataforma_id:
        return getattr(movimento.perfil_plataforma.user, "username", "Individual")
    return "Plataforma"


def obter_metricas_movimentos(queryset):
    return {
        "total_movimentos": queryset.count(),
        "total_valor": somar_valor(queryset),
        "total_pagos": queryset.filter(estado="pago").count(),
        "total_pendentes": queryset.filter(estado="pendente").count(),
    }


def obter_metricas_analytics_financas(queryset):
    total_entradas = somar_valor(queryset, Q(natureza_fluxo=NATUREZA_ENTRADA))
    total_saidas = somar_valor(queryset, Q(natureza_fluxo=NATUREZA_SAIDA))
    saldo = total_entradas - total_saidas
    return {
        "total_movimentos": queryset.count(),
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo": saldo,
        "movimentos_pendentes": queryset.filter(estado="pendente").count(),
        "movimentos_pagos": queryset.filter(estado="pago").count(),
    }


def obter_configuracao_paypal_principal():
    configuracao, _ = ConfiguracaoPagamentoPlataforma.objects.get_or_create(nome="principal")
    return configuracao
