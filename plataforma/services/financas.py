from decimal import Decimal

from django.utils import timezone

from plataforma.models import MovimentoFinanceiroPlataforma
from plataforma.selectors.financas import (
    obter_configuracao_paypal_principal,
    obter_pagamento_empresa_por_pk,
)
from plataforma.services.paypal import PaypalServiceError, capturar_ordem_paypal, criar_ordem_paypal


def guardar_movimento_saida(form):
    return form.save()


def guardar_configuracao_paypal(form):
    return form.save()


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
