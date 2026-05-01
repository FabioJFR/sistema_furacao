from dispositivos.selectors.dashboard import (
    obter_dispositivos_qs,
    obter_leituras_qs,
    obter_sessao_detail,
    obter_sessoes_qs,
    obter_shots_qs,
)


def construir_contexto_dashboard_dispositivos(*, empresa_id):
    dispositivos_qs = obter_dispositivos_qs(empresa_id)
    sessoes_qs = obter_sessoes_qs(empresa_id)
    leituras_qs = obter_leituras_qs(empresa_id)
    shots_qs = obter_shots_qs(empresa_id)

    return {
        "total_dispositivos": dispositivos_qs.count(),
        "total_ativos": dispositivos_qs.filter(ativo=True).count(),
        "total_sessoes": sessoes_qs.count(),
        "total_leituras_brutas": leituras_qs.count(),
        "total_shots": shots_qs.count(),
        "ultima_sessao": (
            sessoes_qs.select_related("dispositivo", "empregado", "furo", "empresa")
            .order_by("-iniciado_em")
            .first()
        ),
        "ultima_leitura_bruta": (
            leituras_qs.select_related("sessao", "empresa")
            .order_by("-recebido_em")
            .first()
        ),
        "ultimo_shot": (
            shots_qs.select_related("sessao", "furo", "empresa")
            .order_by("-criado_em")
            .first()
        ),
    }


def construir_contexto_sessoes_dispositivo(*, empresa_id):
    return {
        "sessoes": obter_sessoes_qs(empresa_id)
        .select_related("dispositivo", "empresa", "empregado", "furo")
        .order_by("-iniciado_em")
    }


def construir_contexto_leituras_brutas_dispositivo(*, empresa_id):
    return {
        "leituras": obter_leituras_qs(empresa_id)
        .select_related("sessao", "empresa")
        .order_by("-recebido_em")
    }


def construir_contexto_shots_dispositivo(*, empresa_id):
    return {
        "shots": obter_shots_qs(empresa_id)
        .select_related("sessao", "empresa", "furo")
        .order_by("-criado_em")
    }


def construir_contexto_lista_dispositivos(*, empresa_id):
    dispositivos = obter_dispositivos_qs(empresa_id).order_by("nome")
    return {
        "dispositivos": dispositivos,
        "total_dispositivos": dispositivos.count(),
    }


def construir_contexto_sessao_dispositivo_detail(*, pk, empresa_id):
    sessao = obter_sessao_detail(pk=pk, empresa_id=empresa_id)
    return {
        "sessao": sessao,
        "leituras_brutas": sessao.leituras_brutas.all().order_by("sequencia"),
        "leituras": sessao.leituras.all().order_by("timestamp_device", "criado_em"),
        "shots": sessao.shots.all().order_by("profundidade"),
    }
