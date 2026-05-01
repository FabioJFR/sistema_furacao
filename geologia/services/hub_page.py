from geologia.selectors.dashboard import (
    listar_documentos_knowledge_base_drone,
    obter_drones_sf_hub_qs,
    obter_furos_geologia_hub_qs,
    obter_logs_geologia_hub_qs,
    obter_missoes_geologia_hub_qs,
)


def construir_contexto_geologia_hub(*, empresa, contexto_geologia):
    furos_qs = obter_furos_geologia_hub_qs(empresa=empresa)
    logs_qs = obter_logs_geologia_hub_qs(empresa=empresa)
    missoes_qs = obter_missoes_geologia_hub_qs(empresa=empresa)

    return {
        "contexto_geologia": contexto_geologia,
        "empresa_geologia": empresa,
        "furos": furos_qs[:12],
        "logs_recentes": logs_qs[:6],
        "missoes_recentes": missoes_qs[:6],
        "total_furos": furos_qs.count(),
        "total_logs": logs_qs.count(),
        "total_missoes": missoes_qs.count(),
    }


def construir_contexto_drone_sf_hub(*, empresa, contexto_geologia):
    furos_qs = obter_furos_geologia_hub_qs(empresa=empresa)
    drones_qs = obter_drones_sf_hub_qs(empresa=empresa)
    missoes_qs = obter_missoes_geologia_hub_qs(empresa=empresa)
    documentos_drone = listar_documentos_knowledge_base_drone()

    return {
        "contexto_geologia": contexto_geologia,
        "empresa_geologia": empresa,
        "total_furos": furos_qs.count(),
        "total_drones_sf": drones_qs.count(),
        "total_missoes": missoes_qs.count(),
        "furos": furos_qs[:10],
        "drones_sf": drones_qs[:8],
        "missoes_recentes": missoes_qs[:6],
        "documentos_drone": documentos_drone,
    }
