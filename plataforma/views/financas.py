from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from plataforma.decorators import platform_admin_required
from plataforma.selectors.financas import obter_configuracao_paypal_principal
from plataforma.services.financas import (
    construir_contexto_analytics_financas,
    construir_contexto_entrada_financeira,
    construir_contexto_paypal_config,
    construir_contexto_saida_financeira,
    obter_movimento_edicao_saida,
    processar_fluxo_checkout_paypal_pagamento,
    processar_fluxo_configuracao_paypal,
    processar_fluxo_retorno_paypal,
    processar_fluxo_saida_financeira,
    validar_acesso_superuser_para_financas,
)


def _aplicar_mensagem_por_nivel(request, acao):
    nivel = acao.get("nivel")
    mensagem = acao.get("mensagem")
    if not mensagem:
        return
    if nivel == "success":
        messages.success(request, mensagem)
    elif nivel == "info":
        messages.info(request, mensagem)
    elif nivel == "warning":
        messages.warning(request, mensagem)
    else:
        messages.error(request, mensagem)


@login_required
@platform_admin_required
def financas_entrada_list(request):
    return render(request, "plataforma/finance_movimento_list.html", construir_contexto_entrada_financeira())


@login_required
@platform_admin_required
def financas_saida_list(request):
    movimento_edicao = obter_movimento_edicao_saida(edicao_id=request.GET.get("editar"))

    fluxo = processar_fluxo_saida_financeira(
        method=request.method,
        post_data=request.POST,
        movimento_edicao=movimento_edicao,
    )
    form = fluxo["form"]
    movimento_edicao = fluxo["movimento_edicao"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            messages.success(request, resultado["mensagem"])
            return redirect("plataforma:financas_saida_list")
        messages.error(request, resultado["mensagem"])

    context = construir_contexto_saida_financeira(
        form=form,
        movimento_edicao=movimento_edicao,
    )
    return render(request, "plataforma/finance_movimento_list.html", context)


@login_required
@platform_admin_required
def financas_analytics(request):
    return render(request, "plataforma/finance_analytics.html", construir_contexto_analytics_financas())


@login_required
@platform_admin_required
def financas_paypal_config(request):
    acesso = validar_acesso_superuser_para_financas(user=request.user)
    if not acesso["ok"]:
        messages.error(request, acesso["mensagem"])
        return redirect("plataforma:financas_analytics")

    configuracao = obter_configuracao_paypal_principal()

    fluxo = processar_fluxo_configuracao_paypal(
        method=request.method,
        post_data=request.POST,
        configuracao=configuracao,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            messages.success(request, resultado["mensagem"])
            return redirect("plataforma:financas_paypal_config")
        messages.error(request, resultado["mensagem"])

    return render(request, "plataforma/finance_paypal_config.html", construir_contexto_paypal_config(form=form))


@login_required
@platform_admin_required
def financas_paypal_checkout_pagamento(request, pk):
    acesso = validar_acesso_superuser_para_financas(user=request.user)
    if not acesso["ok"]:
        messages.error(request, acesso["mensagem"])
        return redirect("plataforma:subscricao_list")

    return_url = (
        request.build_absolute_uri(reverse("plataforma:financas_paypal_retorno"))
        + f"?pagamento={pk}"
    )
    cancel_url = (
        request.build_absolute_uri(reverse("plataforma:financas_paypal_cancelado"))
        + f"?pagamento={pk}"
    )
    acao = processar_fluxo_checkout_paypal_pagamento(
        pagamento_pk=pk,
        return_url=return_url,
        cancel_url=cancel_url,
    )
    if acao["nivel"] == "redirect":
        return redirect(acao["url"])
    _aplicar_mensagem_por_nivel(request, acao)
    return redirect(acao["destino"])


@login_required
@platform_admin_required
def financas_paypal_retorno(request):
    acesso = validar_acesso_superuser_para_financas(user=request.user)
    if not acesso["ok"]:
        messages.error(request, acesso["mensagem"])
        return redirect("plataforma:subscricao_list")

    pagamento_id = (request.GET.get("pagamento") or "").strip()
    token = (request.GET.get("token") or "").strip()
    acao = processar_fluxo_retorno_paypal(
        pagamento_pk=pagamento_id,
        token=token,
    )
    _aplicar_mensagem_por_nivel(request, acao)
    return redirect("plataforma:subscricao_list")


@login_required
@platform_admin_required
def financas_paypal_cancelado(request):
    acesso = validar_acesso_superuser_para_financas(user=request.user)
    if not acesso["ok"]:
        messages.error(request, acesso["mensagem"])
    else:
        messages.info(request, "Pagamento PayPal cancelado pelo utilizador.")
    return redirect("plataforma:subscricao_list")
