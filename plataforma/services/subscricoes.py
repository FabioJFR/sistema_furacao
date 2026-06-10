from plataforma.selectors.subscricoes import (
    listar_subscricoes,
    mapear_contas_admin_por_empresa,
    mapear_pagamentos_pendentes_por_subscricao,
    obter_metricas_ativacao_contas,
    obter_metricas_subscricoes,
)
import logging

from website.services import diagnosticar_email_transacional


logger = logging.getLogger(__name__)


def construir_contexto_subscricao_list(*, perfil):
    subscricoes = list(listar_subscricoes())
    pagamentos_pendentes = mapear_pagamentos_pendentes_por_subscricao(subscricoes)
    contas_admin = mapear_contas_admin_por_empresa(subscricoes)
    for subscricao in subscricoes:
        subscricao.pagamento_pendente = pagamentos_pendentes.get(str(subscricao.pk))
        subscricao.conta_admin = contas_admin.get(str(subscricao.empresa_id))

    metricas = obter_metricas_subscricoes(listar_subscricoes())
    metricas_ativacao = obter_metricas_ativacao_contas(subscricoes)

    try:
        diagnostico_email = diagnosticar_email_transacional()
    except Exception:
        logger.exception("Erro ao diagnosticar email transacional na lista de subscricoes.")
        diagnostico_email = None

    return {
        "perfil": perfil,
        "subscricoes": subscricoes,
        "diagnostico_email": diagnostico_email,
        **metricas,
        **metricas_ativacao,
    }
