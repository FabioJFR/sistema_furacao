from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from plataforma.decorators import platform_admin_required
from plataforma.forms import ConfiguracaoPaypalForm, EntradaValorForm
from plataforma.selectors.financas import (
    NATUREZA_ENTRADA,
    NATUREZA_SAIDA,
    destino_movimento_label,
    listar_movimentos_financeiros,
    obter_configuracao_paypal_principal,
    obter_metricas_analytics_financas,
    obter_metricas_movimentos,
)
from plataforma.services.financas import (
    confirmar_checkout_paypal_pagamento,
    construir_form_saida_valor,
    guardar_configuracao_paypal,
    iniciar_checkout_paypal_pagamento,
    obter_movimento_edicao_saida,
    processar_submissao_saida_financeira,
    resolver_resultado_checkout_paypal,
    resolver_resultado_retorno_paypal,
    validar_acesso_superuser_para_financas,
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
    movimento_edicao = obter_movimento_edicao_saida(edicao_id=request.GET.get("editar"))

    if request.method == "POST":
        resultado = processar_submissao_saida_financeira(post_data=request.POST)
        form = resultado["form"]
        movimento_edicao = resultado["movimento_edicao"]
        if resultado["ok"]:
            messages.success(request, resultado["mensagem"])
            return redirect("plataforma:financas_saida_list")
        messages.error(request, resultado["mensagem"])
    else:
        form = construir_form_saida_valor(movimento_edicao=movimento_edicao)

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
    acesso = validar_acesso_superuser_para_financas(user=request.user)
    if not acesso["ok"]:
        messages.error(request, acesso["mensagem"])
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
    resultado = iniciar_checkout_paypal_pagamento(
        pagamento_pk=pk,
        return_url=return_url,
        cancel_url=cancel_url,
    )
    acao = resolver_resultado_checkout_paypal(resultado)
    if acao["nivel"] == "redirect":
        return redirect(acao["url"])
    if acao["nivel"] == "success":
        messages.success(request, acao["mensagem"])
    elif acao["nivel"] == "info":
        messages.info(request, acao["mensagem"])
    else:
        messages.error(request, acao["mensagem"])
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
    resultado = confirmar_checkout_paypal_pagamento(
        pagamento_pk=pagamento_id,
        token=token,
    )
    acao = resolver_resultado_retorno_paypal(resultado)
    if acao["nivel"] == "success":
        messages.success(request, acao["mensagem"])
    elif acao["nivel"] == "info":
        messages.info(request, acao["mensagem"])
    elif acao["nivel"] == "warning":
        messages.warning(request, acao["mensagem"])
    else:
        messages.error(request, acao["mensagem"])
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
