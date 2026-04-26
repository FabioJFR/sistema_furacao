from inspecao_ai import domain_logic as dl

from ..selectors.analises import listar_analises_empresa_qs


def construir_contexto_analise_list(*, empresa, estado, tipo_documento):
    analises_qs = listar_analises_empresa_qs(empresa)
    if estado:
        analises_qs = analises_qs.filter(estado=estado)
    if tipo_documento:
        analises_qs = analises_qs.filter(tipo_documento=tipo_documento)

    return {
        "analises": dl.filtrar_analises_visiveis(list(analises_qs)),
        "estado_atual": estado,
        "tipo_documento_atual": tipo_documento,
    }


def construir_contexto_analise_detail(*, analise):
    resumo_validacao = dl.construir_resumo_validacao_analise(analise)
    return {
        "analise": analise,
        "resumo_validacao": resumo_validacao,
        "sugestoes_reprocessamento": dl.construir_sugestoes_reprocessamento(analise, resumo_validacao),
        "resumo_ai_relatorio": dl.construir_resumo_ai_relatorio(analise),
    }
