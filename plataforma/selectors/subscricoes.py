from plataforma.models import PagamentoEmpresa, SubscricaoEmpresa


def listar_subscricoes():
    return (
        SubscricaoEmpresa.objects
        .select_related("empresa", "plano")
        .order_by("estado", "-data_inicio", "-criado_em")
    )


def obter_metricas_subscricoes(subscricoes):
    return {
        "total_subscricoes": subscricoes.count(),
        "subscricoes_ativas": subscricoes.filter(estado="ativa").count(),
        "subscricoes_pendentes": subscricoes.filter(estado="pendente").count(),
        "subscricoes_expiradas": subscricoes.filter(estado="expirada").count(),
        "subscricoes_canceladas": subscricoes.filter(estado="cancelada").count(),
    }


def mapear_pagamentos_pendentes_por_subscricao(subscricoes):
    subscricoes_ids = [str(s.pk) for s in subscricoes]
    if not subscricoes_ids:
        return {}

    pagamentos = (
        PagamentoEmpresa.objects.filter(
            subscricao_id__in=subscricoes_ids,
            estado="pendente",
        )
        .order_by("criado_em")
    )
    mapa = {}
    for pagamento in pagamentos:
        chave = str(pagamento.subscricao_id)
        if chave not in mapa:
            mapa[chave] = pagamento
    return mapa
