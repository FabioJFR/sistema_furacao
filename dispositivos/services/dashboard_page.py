from dispositivos.selectors.dashboard import (
    obter_dispositivos_qs,
    obter_leituras_qs,
    obter_sessao_detail,
    obter_sessoes_qs,
    obter_shots_qs,
)


def _formatar_duracao_segundos(segundos):
    if segundos is None:
        return "—"
    if segundos < 60:
        return f"{segundos}s"
    minutos, resto = divmod(segundos, 60)
    if minutos < 60:
        return f"{minutos}m {resto}s"
    horas, minutos = divmod(minutos, 60)
    return f"{horas}h {minutos}m"


def construir_observabilidade_dispositivos(*, dispositivos_qs, sessoes_qs, leituras_qs):
    linhas = []
    for dispositivo in dispositivos_qs.order_by("nome"):
        sessoes_dispositivo = sessoes_qs.filter(dispositivo=dispositivo)
        leituras_dispositivo = leituras_qs.filter(sessao__dispositivo=dispositivo)
        total_sessoes = sessoes_dispositivo.count()
        total_erros = sessoes_dispositivo.filter(status="erro").count()
        total_leituras = leituras_dispositivo.count()
        sessoes_encerradas = sessoes_dispositivo.exclude(terminado_em__isnull=True)

        duracoes = [
            int((sessao.terminado_em - sessao.iniciado_em).total_seconds())
            for sessao in sessoes_encerradas
            if sessao.terminado_em and sessao.iniciado_em
        ]
        latencia_media = round(sum(duracoes) / len(duracoes)) if duracoes else None

        ultima_sessao = sessoes_dispositivo.order_by("-iniciado_em").first()
        ultima_leitura = leituras_dispositivo.order_by("-recebido_em").first()
        ultima_atividade = None
        if ultima_sessao:
            ultima_atividade = ultima_sessao.iniciado_em
        if ultima_leitura and (not ultima_atividade or ultima_leitura.recebido_em > ultima_atividade):
            ultima_atividade = ultima_leitura.recebido_em

        disponibilidade = None
        if total_sessoes:
            disponibilidade = round(((total_sessoes - total_erros) / total_sessoes) * 100)

        linhas.append({
            "dispositivo": dispositivo,
            "total_sessoes": total_sessoes,
            "total_erros": total_erros,
            "total_leituras": total_leituras,
            "disponibilidade_percentual": disponibilidade,
            "latencia_media_segundos": latencia_media,
            "latencia_media_label": _formatar_duracao_segundos(latencia_media),
            "ultima_atividade": ultima_atividade,
        })
    return linhas


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
        "observabilidade_dispositivos": construir_observabilidade_dispositivos(
            dispositivos_qs=dispositivos_qs,
            sessoes_qs=sessoes_qs,
            leituras_qs=leituras_qs,
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
