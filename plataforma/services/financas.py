from django.utils import timezone

from plataforma.models import MovimentoFinanceiroPlataforma


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
