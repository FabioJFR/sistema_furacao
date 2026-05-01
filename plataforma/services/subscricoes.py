from plataforma.selectors.subscricoes import (
    listar_subscricoes,
    mapear_pagamentos_pendentes_por_subscricao,
    obter_metricas_subscricoes,
)


def construir_contexto_subscricao_list(*, perfil):
    subscricoes = list(listar_subscricoes())
    pagamentos_pendentes = mapear_pagamentos_pendentes_por_subscricao(subscricoes)
    for subscricao in subscricoes:
        subscricao.pagamento_pendente = pagamentos_pendentes.get(str(subscricao.pk))

    metricas = obter_metricas_subscricoes(listar_subscricoes())

    return {
        "perfil": perfil,
        "subscricoes": subscricoes,
        **metricas,
    }
