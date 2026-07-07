from decimal import Decimal

from django.utils import timezone

from plataforma.forms import ConfiguracaoPaypalForm, EntradaValorForm, SaidaValorForm
from plataforma.models import MovimentoFinanceiroPlataforma
from plataforma.selectors.financas import (
    NATUREZA_ENTRADA,
    NATUREZA_SAIDA,
    destino_movimento_label,
    listar_movimentos_financeiros,
    obter_configuracao_paypal_principal,
    obter_metricas_analytics_financas,
    obter_metricas_movimentos,
    obter_movimento_saida_por_pk,
    obter_pagamento_empresa_por_pk,
)
from plataforma.services.paypal import PaypalServiceError, capturar_ordem_paypal, criar_ordem_paypal


def guardar_movimento_saida(form):
    return form.save()


def guardar_configuracao_paypal(form):
    return form.save()


def construir_contexto_lista_movimentos_financeiros(
    *,
    titulo,
    descricao,
    tipo_pagina,
    movimentos,
    form,
    movimento_edicao=None,
):
    metricas = obter_metricas_movimentos(movimentos)
    context = {
        "titulo": titulo,
        "descricao": descricao,
        "movimentos": movimentos,
        **metricas,
        "tipo_pagina": tipo_pagina,
        "form": form,
    }
    if movimento_edicao is not None:
        context["movimento_edicao"] = movimento_edicao
    return context


def construir_contexto_entrada_financeira():
    movimentos = listar_movimentos_financeiros(natureza_fluxo=NATUREZA_ENTRADA)
    return construir_contexto_lista_movimentos_financeiros(
        titulo="Entrada de valores",
        descricao="Registos financeiros que representam entradas ou valores a receber pela plataforma.",
        tipo_pagina="entrada",
        movimentos=movimentos,
        form=EntradaValorForm(),
    )


def construir_contexto_saida_financeira(*, form, movimento_edicao):
    movimentos = listar_movimentos_financeiros(natureza_fluxo=NATUREZA_SAIDA)
    return construir_contexto_lista_movimentos_financeiros(
        titulo="Saída de valores",
        descricao=(
            "Despesas e outras saídas financeiras da plataforma, incluindo alojamento, "
            "publicidade, domínio e HTTPS."
        ),
        tipo_pagina="saida",
        movimentos=movimentos,
        form=form,
        movimento_edicao=movimento_edicao,
    )


def construir_contexto_analytics_financas():
    movimentos = listar_movimentos_financeiros()
    metricas = obter_metricas_analytics_financas(movimentos)
    ultimos_movimentos = list(movimentos[:10])
    for movimento in ultimos_movimentos:
        movimento.destino_label = destino_movimento_label(movimento)

    return {
        "titulo": "Analytics Financeiro",
        **metricas,
        "ultimos_movimentos": ultimos_movimentos,
    }


def construir_contexto_paypal_config(*, form):
    return {
        "titulo": "Configuração PayPal",
        "form": form,
    }


def construir_form_configuracao_paypal(*, post_data=None, configuracao=None):
    if post_data is not None:
        return ConfiguracaoPaypalForm(post_data, instance=configuracao)
    return ConfiguracaoPaypalForm(instance=configuracao)


def processar_submissao_configuracao_paypal(*, post_data, configuracao=None):
    form = construir_form_configuracao_paypal(
        post_data=post_data,
        configuracao=configuracao,
    )
    if not form.is_valid():
        return {
            "ok": False,
            "form": form,
            "mensagem": "Erro ao guardar configuração PayPal.",
        }

    guardar_configuracao_paypal(form)
    return {
        "ok": True,
        "form": form,
        "mensagem": "Configuração PayPal atualizada com sucesso.",
    }


def processar_fluxo_configuracao_paypal(*, method, post_data, configuracao=None):
    if method == "POST":
        resultado = processar_submissao_configuracao_paypal(
            post_data=post_data,
            configuracao=configuracao,
        )
        return {
            "form": resultado["form"],
            "resultado": resultado,
        }

    return {
        "form": construir_form_configuracao_paypal(configuracao=configuracao),
        "resultado": None,
    }


def marcar_pagamento_como_pago(pagamento, *, referencia_externa=""):
    hoje = timezone.now().date()
    pagamento.estado = "pago"
    pagamento.data_pagamento = hoje
    if referencia_externa:
        pagamento.referencia = referencia_externa
    pagamento.save(update_fields=["estado", "data_pagamento", "referencia", "atualizado_em"])

    movimento = (
        MovimentoFinanceiroPlataforma.objects.filter(
            subscricao=pagamento.subscricao,
            estado="pendente",
            natureza_fluxo="entrada",
        )
        .order_by("criado_em")
        .first()
    )
    if movimento:
        movimento.estado = "pago"
        movimento.data_pagamento = hoje
        movimento.metodo_pagamento = "paypal"
        if referencia_externa:
            movimento.referencia = referencia_externa
        movimento.save(
            update_fields=["estado", "data_pagamento", "metodo_pagamento", "referencia", "atualizado_em"]
        )

    if pagamento.subscricao and pagamento.subscricao.estado in ["pendente", "suspensa"]:
        pagamento.subscricao.estado = "ativa"
        pagamento.subscricao.save(update_fields=["estado", "atualizado_em"])
        empresa = pagamento.subscricao.empresa
        if empresa and empresa.status in ["teste", "suspensa"]:
            empresa.status = "ativa"
            empresa.ativo = True
            empresa.save(update_fields=["status", "ativo", "atualizado_em"])

    return pagamento


def iniciar_checkout_paypal_pagamento(
    *,
    pagamento_pk,
    return_url,
    cancel_url,
):
    pagamento = obter_pagamento_empresa_por_pk(pagamento_pk)
    if not pagamento:
        return {"estado": "invalido"}

    if pagamento.estado != "pendente":
        return {"estado": "ja_processado"}

    valor_pagamento = Decimal(pagamento.valor or 0)
    if valor_pagamento <= 0:
        marcar_pagamento_como_pago(pagamento, referencia_externa="PAYPAL-GRATUITO")
        return {"estado": "gratuito_pago"}

    configuracao = obter_configuracao_paypal_principal()
    if not configuracao.ativo or not configuracao.paypal_email:
        return {"estado": "config_incompleta"}

    try:
        ordem = criar_ordem_paypal(
            referencia_local=str(pagamento.pk),
            valor=f"{valor_pagamento:.2f}",
            moeda="EUR",
            descricao=f"Pagamento subscrição {pagamento.empresa.nome}",
            return_url=return_url,
            cancel_url=cancel_url,
        )
    except PaypalServiceError as exc:
        return {"estado": "erro_checkout", "erro": str(exc)}

    pagamento.referencia = ordem["order_id"]
    pagamento.save(update_fields=["referencia", "atualizado_em"])
    return {"estado": "checkout_criado", "approve_url": ordem["approve_url"]}


def confirmar_checkout_paypal_pagamento(*, pagamento_pk, token):
    if not pagamento_pk or not token:
        return {"estado": "retorno_invalido"}

    pagamento = obter_pagamento_empresa_por_pk(pagamento_pk)
    if not pagamento:
        return {"estado": "retorno_invalido"}

    if pagamento.estado != "pendente":
        return {"estado": "ja_processado"}

    try:
        captura = capturar_ordem_paypal(token)
    except PaypalServiceError as exc:
        return {"estado": "erro_confirmacao", "erro": str(exc)}

    if captura.get("status") == "COMPLETED":
        marcar_pagamento_como_pago(pagamento, referencia_externa=token)
        return {"estado": "confirmado"}

    return {"estado": "nao_concluido"}


def validar_acesso_superuser_para_financas(*, user):
    if user.is_superuser:
        return {"ok": True, "mensagem": ""}
    return {"ok": False, "mensagem": "Esta ação está reservada ao superuser."}


def resolver_resultado_checkout_paypal(resultado):
    estado = resultado.get("estado")
    if estado in {"invalido", "ja_processado"}:
        return {"nivel": "info", "mensagem": "Este pagamento já não está pendente.", "destino": "plataforma:subscricao_list"}
    if estado == "gratuito_pago":
        return {"nivel": "success", "mensagem": "Pagamento gratuito marcado automaticamente como pago.", "destino": "plataforma:subscricao_list"}
    if estado == "config_incompleta":
        return {"nivel": "error", "mensagem": "Configuração PayPal incompleta ou inativa.", "destino": "plataforma:financas_paypal_config"}
    if estado == "erro_checkout":
        return {
            "nivel": "error",
            "mensagem": f"Erro ao iniciar checkout PayPal: {resultado.get('erro', '')}",
            "destino": "plataforma:financas_paypal_config",
        }
    if estado == "checkout_criado":
        return {"nivel": "redirect", "url": resultado["approve_url"]}
    return {"nivel": "error", "mensagem": "Não foi possível iniciar o checkout PayPal.", "destino": "plataforma:subscricao_list"}


def resolver_resultado_retorno_paypal(resultado):
    estado = resultado.get("estado")
    if estado in {"retorno_invalido", "invalido"}:
        return {"nivel": "error", "mensagem": "Retorno PayPal inválido."}
    if estado == "ja_processado":
        return {"nivel": "info", "mensagem": "Pagamento já processado."}
    if estado == "erro_confirmacao":
        return {"nivel": "error", "mensagem": f"Erro na confirmação PayPal: {resultado.get('erro', '')}"}
    if estado == "confirmado":
        return {"nivel": "success", "mensagem": "Pagamento PayPal confirmado e registado como pago."}
    return {"nivel": "warning", "mensagem": "O pagamento PayPal ainda não ficou concluído."}


def processar_fluxo_checkout_paypal_pagamento(*, pagamento_pk, return_url, cancel_url):
    resultado_checkout = iniciar_checkout_paypal_pagamento(
        pagamento_pk=pagamento_pk,
        return_url=return_url,
        cancel_url=cancel_url,
    )
    return resolver_resultado_checkout_paypal(resultado_checkout)


def processar_fluxo_retorno_paypal(*, pagamento_pk, token):
    resultado_confirmacao = confirmar_checkout_paypal_pagamento(
        pagamento_pk=pagamento_pk,
        token=token,
    )
    return resolver_resultado_retorno_paypal(resultado_confirmacao)


def obter_movimento_edicao_saida(*, edicao_id):
    valor = (edicao_id or "").strip()
    if not valor:
        return None
    return obter_movimento_saida_por_pk(valor)


def construir_form_saida_valor(*, post_data=None, movimento_edicao=None):
    if post_data is not None:
        return SaidaValorForm(post_data, instance=movimento_edicao)
    return SaidaValorForm(instance=movimento_edicao)


def processar_submissao_saida_financeira(*, post_data):
    movimento_edicao = obter_movimento_edicao_saida(edicao_id=post_data.get("movimento_id"))
    form = construir_form_saida_valor(post_data=post_data, movimento_edicao=movimento_edicao)
    if not form.is_valid():
        return {
            "ok": False,
            "form": form,
            "movimento_edicao": movimento_edicao,
            "mensagem": "Erro ao registar despesa. Verifique os dados.",
        }

    guardar_movimento_saida(form)
    return {
        "ok": True,
        "form": form,
        "movimento_edicao": movimento_edicao,
        "mensagem": "Despesa atualizada com sucesso." if movimento_edicao else "Despesa registada com sucesso.",
    }


def processar_fluxo_saida_financeira(*, method, post_data, movimento_edicao=None):
    if method == "POST":
        resultado = processar_submissao_saida_financeira(post_data=post_data)
        return {
            "form": resultado["form"],
            "movimento_edicao": resultado["movimento_edicao"],
            "resultado": resultado,
        }

    return {
        "form": construir_form_saida_valor(movimento_edicao=movimento_edicao),
        "movimento_edicao": movimento_edicao,
        "resultado": None,
    }
