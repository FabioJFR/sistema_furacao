from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from plataforma.decorators import platform_admin_required
from plataforma.forms import EntradaValorForm, SaidaValorForm
from plataforma.selectors.financas import (
    NATUREZA_ENTRADA,
    NATUREZA_SAIDA,
    destino_movimento_label,
    listar_movimentos_financeiros,
    obter_metricas_analytics_financas,
    obter_metricas_movimentos,
    obter_movimento_saida_por_pk,
)
from plataforma.services.financas import guardar_movimento_saida


@login_required
@platform_admin_required
def financas_entrada_list(request):
    movimentos = listar_movimentos_financeiros(natureza_fluxo=NATUREZA_ENTRADA)
    metricas = obter_metricas_movimentos(movimentos)

    context = {
        "titulo": "Entrada de valores",
        "descricao": "Registos financeiros que representam entradas ou valores a receber pela plataforma.",
        "movimentos": movimentos,
        **metricas,
        "tipo_pagina": "entrada",
        "form": EntradaValorForm(),
    }
    return render(request, "plataforma/finance_movimento_list.html", context)


@login_required
@platform_admin_required
def financas_saida_list(request):
    edicao_id = (request.GET.get("editar") or "").strip()
    movimento_edicao = obter_movimento_saida_por_pk(edicao_id) if edicao_id else None

    if request.method == "POST":
        edicao_id_post = (request.POST.get("movimento_id") or "").strip()
        movimento_edicao = obter_movimento_saida_por_pk(edicao_id_post) if edicao_id_post else None

        form = SaidaValorForm(request.POST, instance=movimento_edicao)
        if form.is_valid():
            guardar_movimento_saida(form)
            if movimento_edicao:
                messages.success(request, "Despesa atualizada com sucesso.")
            else:
                messages.success(request, "Despesa registada com sucesso.")
            return redirect("plataforma:financas_saida_list")
        messages.error(request, "Erro ao registar despesa. Verifique os dados.")
    else:
        form = SaidaValorForm(instance=movimento_edicao)

    movimentos = listar_movimentos_financeiros(natureza_fluxo=NATUREZA_SAIDA)
    metricas = obter_metricas_movimentos(movimentos)

    context = {
        "titulo": "Saída de valores",
        "descricao": "Despesas e outras saídas financeiras da plataforma, incluindo alojamento, publicidade, domínio e HTTPS.",
        "movimentos": movimentos,
        **metricas,
        "tipo_pagina": "saida",
        "form": form,
        "movimento_edicao": movimento_edicao,
    }
    return render(request, "plataforma/finance_movimento_list.html", context)


@login_required
@platform_admin_required
def financas_analytics(request):
    movimentos = listar_movimentos_financeiros()
    metricas = obter_metricas_analytics_financas(movimentos)

    ultimos_movimentos = list(movimentos[:10])
    for movimento in ultimos_movimentos:
        movimento.destino_label = destino_movimento_label(movimento)

    context = {
        "titulo": "Analytics Financeiro",
        **metricas,
        "ultimos_movimentos": ultimos_movimentos,
    }
    return render(request, "plataforma/finance_analytics.html", context)
