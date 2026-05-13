from plataforma.selectors.subscricoes import (
    listar_subscricoes,
    mapear_contas_admin_por_empresa,
    mapear_pagamentos_pendentes_por_subscricao,
    obter_metricas_ativacao_contas,
    obter_metricas_subscricoes,
)


def construir_contexto_subscricao_list(*, perfil):
    subscricoes = list(listar_subscricoes())
    pagamentos_pendentes = mapear_pagamentos_pendentes_por_subscricao(subscricoes)
    contas_admin = mapear_contas_admin_por_empresa(subscricoes)
    for subscricao in subscricoes:
        subscricao.pagamento_pendente = pagamentos_pendentes.get(str(subscricao.pk))
        subscricao.conta_admin = contas_admin.get(str(subscricao.empresa_id))

    metricas = obter_metricas_subscricoes(listar_subscricoes())
    metricas_ativacao = obter_metricas_ativacao_contas(subscricoes)

    return {
        "perfil": perfil,
        "subscricoes": subscricoes,
        **metricas,
        **metricas_ativacao,
    }
