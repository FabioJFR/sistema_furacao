from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from plataforma.decorators import platform_admin_required
from plataforma.forms import ConfiguracaoPaypalForm, EntradaValorForm, SaidaValorForm
from plataforma.selectors.financas import (
    NATUREZA_ENTRADA,
    NATUREZA_SAIDA,
    destino_movimento_label,
    listar_movimentos_financeiros,
    obter_configuracao_paypal_principal,
    obter_metricas_analytics_financas,
    obter_metricas_movimentos,
    obter_movimento_saida_por_pk,
)
from plataforma.services.financas import (
    confirmar_checkout_paypal_pagamento,
    guardar_configuracao_paypal,
    guardar_movimento_saida,
    iniciar_checkout_paypal_pagamento,
)


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


@login_required
@platform_admin_required
def financas_paypal_config(request):
    if not request.user.is_superuser:
        messages.error(request, "Esta configuração está reservada ao superuser.")
        return redirect("plataforma:financas_analytics")

    configuracao = obter_configuracao_paypal_principal()

    if request.method == "POST":
        form = ConfiguracaoPaypalForm(request.POST, instance=configuracao)
        if form.is_valid():
            guardar_configuracao_paypal(form)
            messages.success(request, "Configuração PayPal atualizada com sucesso.")
            return redirect("plataforma:financas_paypal_config")
        messages.error(request, "Erro ao guardar configuração PayPal.")
    else:
        form = ConfiguracaoPaypalForm(instance=configuracao)

    return render(
        request,
        "plataforma/finance_paypal_config.html",
        {
            "titulo": "Configuração PayPal",
            "form": form,
        },
    )


@login_required
@platform_admin_required
def financas_paypal_checkout_pagamento(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Esta ação está reservada ao superuser.")
        return redirect("plataforma:subscricao_list")

    return_url = (
        request.build_absolute_uri(reverse("plataforma:financas_paypal_retorno"))
        + f"?pagamento={pk}"
    )
    cancel_url = (
        request.build_absolute_uri(reverse("plataforma:financas_paypal_cancelado"))
        + f"?pagamento={pk}"
    )
    resultado = iniciar_checkout_paypal_pagamento(
        pagamento_pk=pk,
        return_url=return_url,
        cancel_url=cancel_url,
    )

    if resultado["estado"] in {"invalido", "ja_processado"}:
        messages.info(request, "Este pagamento já não está pendente.")
        return redirect("plataforma:subscricao_list")
    if resultado["estado"] == "gratuito_pago":
        messages.success(request, "Pagamento gratuito marcado automaticamente como pago.")
        return redirect("plataforma:subscricao_list")
    if resultado["estado"] == "config_incompleta":
        messages.error(request, "Configuração PayPal incompleta ou inativa.")
        return redirect("plataforma:financas_paypal_config")
    if resultado["estado"] == "erro_checkout":
        messages.error(request, f"Erro ao iniciar checkout PayPal: {resultado.get('erro', '')}")
        return redirect("plataforma:financas_paypal_config")
    if resultado["estado"] == "checkout_criado":
        return redirect(resultado["approve_url"])
    messages.error(request, "Não foi possível iniciar o checkout PayPal.")
    return redirect("plataforma:subscricao_list")


@login_required
@platform_admin_required
def financas_paypal_retorno(request):
    if not request.user.is_superuser:
        messages.error(request, "Esta ação está reservada ao superuser.")
        return redirect("plataforma:subscricao_list")

    pagamento_id = (request.GET.get("pagamento") or "").strip()
    token = (request.GET.get("token") or "").strip()
    resultado = confirmar_checkout_paypal_pagamento(
        pagamento_pk=pagamento_id,
        token=token,
    )

    if resultado["estado"] in {"retorno_invalido", "invalido"}:
        messages.error(request, "Retorno PayPal inválido.")
        return redirect("plataforma:subscricao_list")
    if resultado["estado"] == "ja_processado":
        messages.info(request, "Pagamento já processado.")
        return redirect("plataforma:subscricao_list")
    if resultado["estado"] == "erro_confirmacao":
        messages.error(request, f"Erro na confirmação PayPal: {resultado.get('erro', '')}")
        return redirect("plataforma:subscricao_list")
    if resultado["estado"] == "confirmado":
        messages.success(request, "Pagamento PayPal confirmado e registado como pago.")
    else:
        messages.warning(request, "O pagamento PayPal ainda não ficou concluído.")

    return redirect("plataforma:subscricao_list")


@login_required
@platform_admin_required
def financas_paypal_cancelado(request):
    if not request.user.is_superuser:
        messages.error(request, "Esta ação está reservada ao superuser.")
    else:
        messages.info(request, "Pagamento PayPal cancelado pelo utilizador.")
    return redirect("plataforma:subscricao_list")
