from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from plataforma.decorators import platform_admin_required
from plataforma.models import MovimentoFinanceiroPlataforma
from plataforma.forms import EntradaValorForm, SaidaValorForm


NATUREZA_ENTRADA = "entrada"
NATUREZA_SAIDA = "saida"


def _somar(queryset, filtro=None):
    aggregate_kwargs = {}
    if filtro is not None:
        aggregate_kwargs["filter"] = filtro
    total = queryset.aggregate(total=Sum("valor", **aggregate_kwargs))["total"]
    return total or Decimal("0.00")


def _destino_movimento(movimento):
    if movimento.empresa_id:
        return movimento.empresa.nome
    if movimento.perfil_plataforma_id:
        return getattr(movimento.perfil_plataforma.user, "username", "Individual")
    return "Plataforma"


@login_required
@platform_admin_required
def financas_entrada_list(request):
    movimentos = (
        MovimentoFinanceiroPlataforma.objects
        .select_related("empresa", "perfil_plataforma__user", "plano", "subscricao")
        .filter(natureza_fluxo=NATUREZA_ENTRADA)
        .order_by("-data_vencimento", "-criado_em")
    )

    context = {
        "titulo": "Entrada de valores",
        "descricao": "Registos financeiros que representam entradas ou valores a receber pela plataforma.",
        "movimentos": movimentos,
        "total_movimentos": movimentos.count(),
        "total_valor": _somar(movimentos),
        "total_pagos": movimentos.filter(estado="pago").count(),
        "total_pendentes": movimentos.filter(estado="pendente").count(),
        "tipo_pagina": "entrada",
        "form": EntradaValorForm(),
    }
    return render(request, "plataforma/finance_movimento_list.html", context)


@login_required
@platform_admin_required
def financas_saida_list(request):
    edicao_id = (request.GET.get("editar") or "").strip()
    movimento_edicao = None
    if edicao_id:
        movimento_edicao = get_object_or_404(
            MovimentoFinanceiroPlataforma.objects.filter(natureza_fluxo=NATUREZA_SAIDA),
            pk=edicao_id,
        )

    if request.method == "POST":
        edicao_id_post = (request.POST.get("movimento_id") or "").strip()
        movimento_edicao = None
        if edicao_id_post:
            movimento_edicao = get_object_or_404(
                MovimentoFinanceiroPlataforma.objects.filter(natureza_fluxo=NATUREZA_SAIDA),
                pk=edicao_id_post,
            )

        form = SaidaValorForm(request.POST, instance=movimento_edicao)
        if form.is_valid():
            form.save()
            if movimento_edicao:
                messages.success(request, "Despesa atualizada com sucesso.")
            else:
                messages.success(request, "Despesa registada com sucesso.")
            return redirect("plataforma:financas_saida_list")
        messages.error(request, "Erro ao registar despesa. Verifique os dados.")
    else:
        form = SaidaValorForm(instance=movimento_edicao)

    movimentos = (
        MovimentoFinanceiroPlataforma.objects
        .select_related("empresa", "perfil_plataforma__user", "plano", "subscricao")
        .filter(natureza_fluxo=NATUREZA_SAIDA)
        .order_by("-data_vencimento", "-criado_em")
    )

    context = {
        "titulo": "Saída de valores",
        "descricao": "Despesas e outras saídas financeiras da plataforma, incluindo alojamento, publicidade, domínio e HTTPS.",
        "movimentos": movimentos,
        "total_movimentos": movimentos.count(),
        "total_valor": _somar(movimentos),
        "total_pagos": movimentos.filter(estado="pago").count(),
        "total_pendentes": movimentos.filter(estado="pendente").count(),
        "tipo_pagina": "saida",
        "form": form,
        "movimento_edicao": movimento_edicao,
    }
    return render(request, "plataforma/finance_movimento_list.html", context)


@login_required
@platform_admin_required
def financas_analytics(request):
    movimentos = (
        MovimentoFinanceiroPlataforma.objects
        .select_related("empresa", "perfil_plataforma__user", "plano", "subscricao")
        .order_by("-data_vencimento", "-criado_em")
    )

    total_entradas = _somar(movimentos, Q(natureza_fluxo=NATUREZA_ENTRADA))
    total_saidas = _somar(movimentos, Q(natureza_fluxo=NATUREZA_SAIDA))
    saldo = total_entradas - total_saidas

    ultimos_movimentos = list(movimentos[:10])
    for movimento in ultimos_movimentos:
        movimento.destino_label = _destino_movimento(movimento)

    context = {
        "titulo": "Analytics Financeiro",
        "total_movimentos": movimentos.count(),
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo": saldo,
        "movimentos_pendentes": movimentos.filter(estado="pendente").count(),
        "movimentos_pagos": movimentos.filter(estado="pago").count(),
        "ultimos_movimentos": ultimos_movimentos,
    }
    return render(request, "plataforma/finance_analytics.html", context)
