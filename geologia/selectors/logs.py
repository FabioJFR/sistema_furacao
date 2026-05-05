from django.shortcuts import get_object_or_404

from geologia.models import LogGeologicoFuro
from django.db.models import Avg, Sum

from projetos.models import Furo, RegistoDiarioEmpregado


LITOLOGIA_CORES_BASE = {
    "granito": "#8b7d6b",
    "quartzo": "#f2f2f2",
    "solo": "#8a5a2b",
    "xisto escuro": "#2f3640",
    "xisto claro": "#7f8fa6",
    "argila": "#b5654d",
    "minério": "#a84f1d",
    "pirite": "#c9a227",
    "jaspe": "#b03a00",
    "calcário": "#c9c3b5",
    "arenito": "#be9a5f",
    "basalto": "#2c3e50",
    "gnaisse": "#8d8176",
    "dolomito": "#bfb8a6",
    "mármore": "#e5e3dd",
}


def filtrar_queryset_por_empresa(queryset, empresa=None):
    if empresa is None:
        return queryset
    return queryset.filter(empresa=empresa)


def obter_furo_log_geologico(furo_id, empresa=None):
    queryset = filtrar_queryset_por_empresa(Furo.objects.select_related("projeto"), empresa=empresa)
    return get_object_or_404(queryset, pk=furo_id)


def obter_log_geologico(pk, empresa=None):
    logs_qs = filtrar_queryset_por_empresa(
        LogGeologicoFuro.objects.select_related("furo", "furo__projeto", "medicao", "missao_drone"),
        empresa=empresa,
    )
    return get_object_or_404(logs_qs, pk=pk)


def obter_anexos_log(log):
    return log.anexos.all().order_by("-criado_em")


def obter_logs_pendentes_validacao(*, empresa=None):
    queryset = LogGeologicoFuro.objects.select_related(
        "furo",
        "furo__projeto",
        "medicao",
        "missao_drone",
        "validado_por",
    ).filter(status_validacao="pendente")
    return filtrar_queryset_por_empresa(queryset, empresa=empresa).order_by("-data_registo", "-criado_em")


def obter_logs_geologicos_recentes_furo(furo, *, empresa=None, limit=5):
    queryset = LogGeologicoFuro.objects.filter(furo=furo)
    queryset = filtrar_queryset_por_empresa(queryset, empresa=empresa)
    return (
        queryset
        .select_related("missao_drone", "medicao")
        .order_by("-data_registo", "-criado_em")[:limit]
    )


def obter_conflitos_intervalos_logs(*, empresa=None):
    logs = list(
        filtrar_queryset_por_empresa(
            LogGeologicoFuro.objects.select_related("furo", "furo__projeto"),
            empresa=empresa,
        ).order_by("furo_id", "intervalo_de", "intervalo_ate", "criado_em")
    )
    conflitos = []
    por_furo = {}
    for log in logs:
        por_furo.setdefault(log.furo_id, []).append(log)

    for _furo_id, itens in por_furo.items():
        for idx, atual in enumerate(itens):
            for prox in itens[idx + 1:]:
                if prox.intervalo_de > atual.intervalo_ate:
                    break
                # Conflito só existe com sobreposição real.
                # Encostar limite com limite (A acaba onde B começa) é permitido.
                if atual.intervalo_de < prox.intervalo_ate and prox.intervalo_de < atual.intervalo_ate:
                    conflitos.append(
                        {
                            "furo": atual.furo,
                            "projeto": atual.furo.projeto,
                            "log_a": atual,
                            "log_b": prox,
                            "intervalo_conflito_de": max(atual.intervalo_de, prox.intervalo_de),
                            "intervalo_conflito_ate": min(atual.intervalo_ate, prox.intervalo_ate),
                        }
                    )
    return conflitos


def obter_logs_envolvidos_conflito(*, furo, conflito_de, conflito_ate, empresa=None):
    queryset = LogGeologicoFuro.objects.select_related("furo", "furo__projeto").filter(
        furo=furo,
        # Apenas sobreposição real (não inclui intervalos apenas encostados no limite).
        intervalo_de__lt=conflito_ate,
        intervalo_ate__gt=conflito_de,
    )
    queryset = filtrar_queryset_por_empresa(queryset, empresa=empresa)
    return queryset.order_by("intervalo_de", "intervalo_ate", "criado_em")


def obter_planeamento_amostragem_geologo(*, empresa=None, intervalo_padrao=10.0):
    furos_qs = filtrar_queryset_por_empresa(
        Furo.objects.select_related("projeto").order_by("nome"),
        empresa=empresa,
    )
    logs_qs = filtrar_queryset_por_empresa(
        LogGeologicoFuro.objects.select_related("furo"),
        empresa=empresa,
    ).order_by("furo_id", "-intervalo_ate", "-criado_em")

    ultimo_por_furo = {}
    for log in logs_qs:
        if log.furo_id not in ultimo_por_furo:
            ultimo_por_furo[log.furo_id] = log

    linhas = []
    for furo in furos_qs:
        ultimo_log = ultimo_por_furo.get(furo.id)
        inicio_sugerido = float(ultimo_log.intervalo_ate) if ultimo_log else 0.0
        fim_sugerido = inicio_sugerido + float(intervalo_padrao or 10.0)
        linhas.append(
            {
                "furo": furo,
                "projeto": furo.projeto,
                "ultimo_log": ultimo_log,
                "profundidade_atual": float(furo.profundidade_atual or 0.0),
                "inicio_sugerido": round(inicio_sugerido, 2),
                "fim_sugerido": round(fim_sugerido, 2),
            }
        )
    return linhas


def obter_qualidade_dados_logs_geologo(*, empresa=None):
    logs = list(
        filtrar_queryset_por_empresa(
            LogGeologicoFuro.objects.select_related("furo", "furo__projeto"),
            empresa=empresa,
        ).order_by("-data_registo", "-criado_em")
    )
    conflitos = obter_conflitos_intervalos_logs(empresa=empresa)
    conflitos_ids = set()
    for c in conflitos:
        conflitos_ids.add(c["log_a"].id)
        conflitos_ids.add(c["log_b"].id)

    linhas = []
    for log in logs:
        problemas = []
        if log.intervalo_de is None or log.intervalo_ate is None or float(log.intervalo_de) >= float(log.intervalo_ate):
            problemas.append("Intervalo inválido")
        if not (log.litologia_principal or "").strip():
            problemas.append("Litologia em falta")
        if not log.anexos.exists():
            problemas.append("Sem anexos")
        if log.id in conflitos_ids:
            problemas.append("Conflito de intervalo")

        if problemas:
            linhas.append(
                {
                    "log": log,
                    "furo": log.furo,
                    "projeto": log.furo.projeto,
                    "problemas": problemas,
                }
            )
    return linhas


def obter_correlacoes_geologia_perfuracao(*, empresa=None):
    logs = list(
        filtrar_queryset_por_empresa(
            LogGeologicoFuro.objects.select_related("furo", "furo__projeto", "medicao"),
            empresa=empresa,
        ).order_by("-data_registo", "-criado_em")
    )

    linhas = []
    for log in logs:
        agregados = (
            RegistoDiarioEmpregado.objects.filter(
                empresa=log.empresa,
                furo=log.furo,
                data=log.data_registo,
            )
            .aggregate(
                metros=Sum("metros_furados"),
                horas=Sum("horas_trabalhadas"),
            )
        )

        metros = float(agregados.get("metros") or 0.0)
        horas = float(agregados.get("horas") or 0.0)
        produtividade = (metros / horas) if horas > 0 else 0.0

        magnetismo_medio = None
        if log.medicao_id and log.medicao and log.medicao.magnetismo is not None:
            magnetismo_medio = float(log.medicao.magnetismo)
        else:
            magnetismo_medio = (
                log.furo.medicoes.filter(empresa=log.empresa).aggregate(avg=Avg("magnetismo")).get("avg")
            )
            magnetismo_medio = float(magnetismo_medio) if magnetismo_medio is not None else None

        linhas.append(
            {
                "log": log,
                "projeto": log.furo.projeto,
                "furo": log.furo,
                "litologia": (log.litologia_principal or "").strip() or "Sem litologia",
                "metros_dia": round(metros, 2),
                "horas_dia": round(horas, 2),
                "produtividade_m_h": round(produtividade, 2),
                "magnetismo_medio": round(magnetismo_medio, 2) if magnetismo_medio is not None else None,
            }
        )

    return linhas


def obter_mapa_furos_geologo(*, empresa=None, projeto_id=None):
    furos_qs = filtrar_queryset_por_empresa(
        Furo.objects.select_related("projeto").order_by("projeto__nome", "nome"),
        empresa=empresa,
    )
    if projeto_id:
        furos_qs = furos_qs.filter(projeto_id=projeto_id)

    linhas = []
    for furo in furos_qs:
        linhas.append(
            {
                "furo": furo,
                "projeto": furo.projeto,
                "estado": furo.estado,
                "profundidade_atual": float(furo.profundidade_atual or 0.0),
                "latitude": furo.latitude,
                "longitude": furo.longitude,
                "tem_coordenadas": furo.latitude is not None and furo.longitude is not None,
            }
        )
    return linhas


def _cor_litologia(nome):
    if not nome:
        return "#94a3b8"
    key = str(nome).strip().lower()
    if key in LITOLOGIA_CORES_BASE:
        return LITOLOGIA_CORES_BASE[key]
    # cor estável para litologias novas
    h = abs(hash(key)) % 360
    return f"hsl({h} 40% 55%)"


def obter_mapa_litologico_furo(*, furo, empresa=None):
    logs_qs = filtrar_queryset_por_empresa(
        LogGeologicoFuro.objects.filter(furo=furo),
        empresa=empresa,
    ).order_by("intervalo_de", "intervalo_ate", "criado_em")

    logs = list(logs_qs)
    max_depth = max((float(item.intervalo_ate or 0.0) for item in logs), default=float(furo.profundidade_atual or 0.0),)
    max_depth = max(max_depth, 1.0)

    segmentos = []
    legenda = {}
    for item in logs:
        de = float(item.intervalo_de or 0.0)
        ate = float(item.intervalo_ate or de)
        lit = (item.litologia_principal or "Sem litologia").strip()
        cor = _cor_litologia(lit)
        top_pct = (de / max_depth) * 100.0
        height_pct = max(((ate - de) / max_depth) * 100.0, 1.2)
        segmentos.append(
            {
                "log_id": item.id,
                "litologia": lit,
                "cor": cor,
                "de": de,
                "ate": ate,
                "top_pct": min(max(top_pct, 0.0), 100.0),
                "height_pct": min(max(height_pct, 0.6), 100.0),
            }
        )
        if lit not in legenda:
            legenda[lit] = {"cor": cor, "top_pct": top_pct}
        else:
            legenda[lit]["top_pct"] = min(legenda[lit]["top_pct"], top_pct)

    # Evita problemas de locale no CSS inline (ex.: 12,5% em vez de 12.5%).
    for seg in segmentos:
        seg["top_pct_css"] = f"{float(seg['top_pct']):.4f}"
        seg["height_pct_css"] = f"{float(seg['height_pct']):.4f}"
        seg["de_fmt"] = f"{float(seg['de']):.1f}"
        seg["ate_fmt"] = f"{float(seg['ate']):.1f}"

    # Legenda ordenada pela profundidade de primeira ocorrência (topo -> fundo).
    legenda_ordenada = [
        {"litologia": lit, "cor": meta["cor"], "top_pct": meta["top_pct"]}
        for lit, meta in sorted(legenda.items(), key=lambda item: item[1]["top_pct"])
    ]

    return {
        "furo": furo,
        "segmentos": segmentos,
        "legenda": legenda_ordenada,
        "max_depth": round(max_depth, 2),
        "total_logs": len(segmentos),
    }


def obter_alertas_geotecnicos(*, empresa=None):
    logs = list(
        filtrar_queryset_por_empresa(
            LogGeologicoFuro.objects.select_related("furo", "furo__projeto"),
            empresa=empresa,
        ).order_by("-data_registo", "-criado_em")
    )
    alertas = []
    for log in logs:
        if log.rqd_percent is not None and float(log.rqd_percent) < 40:
            alertas.append(
                {
                    "tipo": "RQD baixo",
                    "severidade": "alta" if float(log.rqd_percent) < 25 else "media",
                    "valor": f"{float(log.rqd_percent):.1f}%",
                    "limite": "< 40%",
                    "log": log,
                    "furo": log.furo,
                    "projeto": log.furo.projeto,
                }
            )
        fr_txt = (log.densidade_fraturas or "").strip().lower()
        if fr_txt and any(tag in fr_txt for tag in ["alta", "elevada", "muito alta", "intensa"]):
            alertas.append(
                {
                    "tipo": "Fraturação elevada",
                    "severidade": "media",
                    "valor": log.densidade_fraturas,
                    "limite": "texto geológico com nível elevado",
                    "log": log,
                    "furo": log.furo,
                    "projeto": log.furo.projeto,
                }
            )
        if log.nivel_agua_m is not None and float(log.nivel_agua_m) >= 3:
            alertas.append(
                {
                    "tipo": "Água elevada",
                    "severidade": "alta" if float(log.nivel_agua_m) >= 8 else "media",
                    "valor": f"{float(log.nivel_agua_m):.2f} m",
                    "limite": ">= 3.00 m",
                    "log": log,
                    "furo": log.furo,
                    "projeto": log.furo.projeto,
                }
            )

    prioridade = {"alta": 0, "media": 1, "baixa": 2}
    alertas.sort(key=lambda item: (prioridade.get(item["severidade"], 9), -item["log"].data_registo.toordinal()))
    return alertas


def construir_linhas_relatorio_geologico(*, empresa=None, furo=None):
    queryset = filtrar_queryset_por_empresa(
        LogGeologicoFuro.objects.select_related("furo", "furo__projeto", "missao_drone", "validado_por").prefetch_related("anexos"),
        empresa=empresa,
    )
    if furo is not None:
        queryset = queryset.filter(furo=furo)
    queryset = queryset.order_by("furo__nome", "intervalo_de", "intervalo_ate", "criado_em")

    linhas = []
    for log in queryset:
        anexos = list(log.anexos.all())
        linhas.append(
            {
                "projeto": getattr(log.furo.projeto, "nome", ""),
                "furo": getattr(log.furo, "nome", ""),
                "data_registo": log.data_registo.isoformat() if log.data_registo else "",
                "intervalo_de_m": float(log.intervalo_de or 0.0),
                "intervalo_ate_m": float(log.intervalo_ate or 0.0),
                "litologia_principal": log.litologia_principal or "",
                "litologia_secundaria": log.litologia_secundaria or "",
                "rqd_percent": log.rqd_percent if log.rqd_percent is not None else "",
                "recuperacao_percent": log.recuperacao_testemunho_percent if log.recuperacao_testemunho_percent is not None else "",
                "nivel_agua_m": log.nivel_agua_m if log.nivel_agua_m is not None else "",
                "densidade_fraturas": log.densidade_fraturas or "",
                "missao_drone": getattr(log.missao_drone, "titulo", ""),
                "total_anexos": len(anexos),
                "anexos_titulos": " | ".join([(a.titulo or "").strip() for a in anexos if a.titulo])[:1200],
                "status_validacao": log.status_validacao,
                "validado_por": getattr(log.validado_por, "username", "") if log.validado_por_id else "",
                "validado_em": log.validado_em.isoformat() if log.validado_em else "",
                "observacao_validacao": log.observacao_validacao or "",
                "observacoes": (log.observacoes or "")[:2000],
            }
        )
    return linhas


def construir_resumo_executivo_geologico(linhas):
    total_logs = len(linhas)
    furos = {row.get("furo") for row in linhas if row.get("furo")}
    projetos = {row.get("projeto") for row in linhas if row.get("projeto")}
    litologias = {row.get("litologia_principal") for row in linhas if row.get("litologia_principal")}
    total_anexos = 0
    soma_rqd = 0.0
    count_rqd = 0
    criticos = 0
    for row in linhas:
        try:
            total_anexos += int(row.get("total_anexos") or 0)
        except (TypeError, ValueError):
            pass
        rqd = row.get("rqd_percent")
        if rqd not in ("", None):
            try:
                rqd_f = float(rqd)
                soma_rqd += rqd_f
                count_rqd += 1
                if rqd_f < 40:
                    criticos += 1
            except (TypeError, ValueError):
                pass
    return {
        "total_logs": total_logs,
        "total_furos": len(furos),
        "total_projetos": len(projetos),
        "total_litologias": len(litologias),
        "total_anexos": total_anexos,
        "rqd_medio": round((soma_rqd / count_rqd), 2) if count_rqd else None,
        "logs_rqd_critico": criticos,
    }
