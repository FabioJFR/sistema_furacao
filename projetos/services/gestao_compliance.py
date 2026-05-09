import calendar
from datetime import date, datetime, time, timedelta

from django.db.models import Count
from django.utils import timezone

from plataforma.services.empresas import normalizar_compliance_score_config
from projetos.models import (
    AcaoCorretiva,
    AcaoPreventiva,
    AuditoriaHSE,
    FechoAcaoCorretiva,
    NotificacaoGestao,
    PlanoAuditoriaHSE,
)

SLA_DIAS_POR_PRIORIDADE = {
    "baixa": 30,
    "media": 14,
    "alta": 7,
    "critica": 3,
}

ALERTA_PREVENTIVO_DIAS_POR_PRIORIDADE = {
    "baixa": 10,
    "media": 7,
    "alta": 4,
    "critica": 2,
}


def guardar_evidencia_compliance_form(
    *,
    form,
    empresa,
    user=None,
    checklist=None,
    incidente=None,
    auditoria=None,
    acao_corretiva=None,
    acao_preventiva=None,
):
    evidencia = form.save(commit=False)
    evidencia.empresa = empresa
    evidencia.criado_por = user
    evidencia.checklist = checklist
    evidencia.incidente = incidente
    evidencia.auditoria = auditoria
    evidencia.acao_corretiva = acao_corretiva
    evidencia.acao_preventiva = acao_preventiva
    evidencia.save()
    return evidencia


def registar_fecho_formal_acao_corretiva(*, acao, user, cleaned_data):
    data_fecho = cleaned_data.get("data_fecho") or timezone.localdate()
    fecho, _ = FechoAcaoCorretiva.objects.update_or_create(
        acao=acao,
        defaults={
            "empresa": acao.empresa,
            "fechado_por": user,
            "data_fecho": data_fecho,
            "resumo_execucao": cleaned_data.get("resumo_execucao", ""),
            "eficaz": bool(cleaned_data.get("eficaz")),
            "observacoes": cleaned_data.get("observacoes", ""),
        },
    )
    acao.status = "concluida"
    acao.concluida_em = data_fecho
    acao.save(update_fields=["status", "concluida_em", "atualizado_em"])
    return fecho


def _add_months(base_date: date, months: int) -> date:
    month_index = (base_date.month - 1) + months
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calcular_proxima_execucao_plano(*, data_base: date, frequencia: str) -> date:
    if frequencia == "mensal":
        return _add_months(data_base, 1)
    if frequencia == "trimestral":
        return _add_months(data_base, 3)
    if frequencia == "semestral":
        return _add_months(data_base, 6)
    if frequencia == "anual":
        return _add_months(data_base, 12)
    return _add_months(data_base, 1)


def gerar_auditorias_recorrentes_pendentes(*, empresa, user=None, referencia=None):
    referencia = referencia or timezone.localdate()
    planos = list(
        PlanoAuditoriaHSE.objects.filter(
            empresa=empresa,
            ativo=True,
            proxima_execucao__lte=referencia,
        ).select_related("projeto", "responsavel")
    )
    geradas = []
    for plano in planos:
        auditoria = AuditoriaHSE.objects.create(
            empresa=empresa,
            projeto=plano.projeto,
            responsavel=plano.responsavel,
            titulo=plano.titulo,
            area=plano.area,
            data_auditoria=plano.proxima_execucao,
            status="planeada",
            resultado="observacao",
            observacoes=(plano.observacoes or "").strip(),
        )
        plano.ultima_geracao_em = referencia
        plano.proxima_execucao = calcular_proxima_execucao_plano(
            data_base=plano.proxima_execucao,
            frequencia=plano.frequencia,
        )
        plano.save(update_fields=["ultima_geracao_em", "proxima_execucao", "atualizado_em"])
        geradas.append(auditoria)
    return geradas


def _novo_item_eficacia(nome):
    return {
        "nome": nome or "Sem definição",
        "total": 0,
        "corretivas": 0,
        "preventivas": 0,
        "abertas": 0,
        "concluidas": 0,
        "vencidas": 0,
        "evidencias": 0,
        "dias_fecho_total": 0.0,
        "fechos_com_tempo": 0,
        "dentro_sla": 0,
        "fora_sla": 0,
        "tempo_medio_fecho": 0.0,
        "taxa_sla": 0.0,
        "taxa_fecho": 0.0,
    }


def obter_sla_dias_por_prioridade(prioridade):
    return SLA_DIAS_POR_PRIORIDADE.get(prioridade or "media", 14)


def obter_janela_alerta_preventivo(prioridade):
    return ALERTA_PREVENTIVO_DIAS_POR_PRIORIDADE.get(prioridade or "media", 7)


def calcular_dias_fecho_acao(acao):
    if not acao.concluida_em or not acao.criado_em:
        return None
    dias = (acao.concluida_em - acao.criado_em.date()).days
    return max(dias, 0)


def _obter_nome_equipa_responsavel(responsavel):
    if not responsavel:
        return "Sem função"
    if getattr(responsavel, "funcao", None):
        return responsavel.get_funcao_display()
    return "Sem função"


def _inicio_mes(data_referencia):
    return data_referencia.replace(day=1)


def _fim_mes(data_referencia):
    proximo_mes = _add_months(_inicio_mes(data_referencia), 1)
    return proximo_mes - timedelta(days=1)


def _iterar_periodos_mensais(referencia, total=6):
    base = _inicio_mes(referencia)
    periodos = []
    for offset in range(total - 1, -1, -1):
        inicio = _add_months(base, -offset)
        periodos.append(
            {
                "inicio": inicio,
                "fim": _fim_mes(inicio),
                "mes": inicio.strftime("%m/%Y"),
                "novas": 0,
                "concluidas": 0,
                "abertas": 0,
                "vencidas": 0,
                "dentro_sla": 0,
                "fora_sla": 0,
                "dias_fecho_total": 0.0,
                "fechos_com_tempo": 0,
                "tempo_medio_fecho": 0.0,
                "taxa_sla": 0.0,
            }
        )
    return periodos


def _label_trimestre(data_referencia):
    trimestre = ((data_referencia.month - 1) // 3) + 1
    return f"T{trimestre}/{data_referencia.year}"


def _inicio_trimestre(data_referencia):
    trimestre = ((data_referencia.month - 1) // 3)
    mes_inicio = (trimestre * 3) + 1
    return date(data_referencia.year, mes_inicio, 1)


def _fim_trimestre(data_referencia):
    return _add_months(_inicio_trimestre(data_referencia), 3) - timedelta(days=1)


def _iterar_periodos_trimestrais(referencia, total=4):
    base = _inicio_trimestre(referencia)
    periodos = []
    for offset in range(total - 1, -1, -1):
        inicio = _add_months(base, -(offset * 3))
        periodos.append(
            {
                "inicio": inicio,
                "fim": _fim_trimestre(inicio),
                "periodo": _label_trimestre(inicio),
                "novas": 0,
                "concluidas": 0,
                "abertas": 0,
                "vencidas": 0,
                "dentro_sla": 0,
                "fora_sla": 0,
                "dias_fecho_total": 0.0,
                "fechos_com_tempo": 0,
                "tempo_medio_fecho": 0.0,
                "taxa_sla": 0.0,
            }
        )
    return periodos


def _acao_esta_aberta_em(acao, data_referencia):
    criado_em = getattr(acao, "criado_em", None)
    if not criado_em or criado_em.date() > data_referencia:
        return False
    if getattr(acao, "status", None) == "cancelada":
        return False
    concluida_em = getattr(acao, "concluida_em", None)
    return not concluida_em or concluida_em > data_referencia


def _acao_relevante_na_janela(acao, inicio_janela, fim_janela):
    criado_em = getattr(acao, "criado_em", None)
    concluida_em = getattr(acao, "concluida_em", None)
    prazo = getattr(acao, "prazo", None)

    if criado_em and inicio_janela <= criado_em.date() <= fim_janela:
        return True
    if concluida_em and inicio_janela <= concluida_em <= fim_janela:
        return True
    if prazo and inicio_janela <= prazo <= fim_janela:
        return True
    return _acao_esta_aberta_em(acao, fim_janela)


def _construir_historico_compliance(*, acoes, referencia):
    periodos = _iterar_periodos_mensais(referencia, total=6)
    for periodo in periodos:
        for acao in acoes:
            criado_data = acao.criado_em.date()
            concluida_data = getattr(acao, "concluida_em", None)
            if periodo["inicio"] <= criado_data <= periodo["fim"]:
                periodo["novas"] += 1
            if concluida_data and periodo["inicio"] <= concluida_data <= periodo["fim"]:
                periodo["concluidas"] += 1
                dias_fecho = calcular_dias_fecho_acao(acao)
                if dias_fecho is not None:
                    periodo["dias_fecho_total"] += dias_fecho
                    periodo["fechos_com_tempo"] += 1
                    if dias_fecho <= obter_sla_dias_por_prioridade(getattr(acao, "prioridade", "media")):
                        periodo["dentro_sla"] += 1
                    else:
                        periodo["fora_sla"] += 1
            if _acao_esta_aberta_em(acao, periodo["fim"]):
                periodo["abertas"] += 1
                if acao.prazo and acao.prazo < periodo["fim"]:
                    periodo["vencidas"] += 1

        if periodo["fechos_com_tempo"]:
            periodo["tempo_medio_fecho"] = round(periodo["dias_fecho_total"] / periodo["fechos_com_tempo"], 1)
            periodo["taxa_sla"] = round((periodo["dentro_sla"] / periodo["fechos_com_tempo"]) * 100, 1)
    return periodos


def _construir_historico_trimestral_compliance(*, acoes, referencia):
    periodos = _iterar_periodos_trimestrais(referencia, total=4)
    for periodo in periodos:
        for acao in acoes:
            criado_data = acao.criado_em.date()
            concluida_data = getattr(acao, "concluida_em", None)
            if periodo["inicio"] <= criado_data <= periodo["fim"]:
                periodo["novas"] += 1
            if concluida_data and periodo["inicio"] <= concluida_data <= periodo["fim"]:
                periodo["concluidas"] += 1
                dias_fecho = calcular_dias_fecho_acao(acao)
                if dias_fecho is not None:
                    periodo["dias_fecho_total"] += dias_fecho
                    periodo["fechos_com_tempo"] += 1
                    if dias_fecho <= obter_sla_dias_por_prioridade(getattr(acao, "prioridade", "media")):
                        periodo["dentro_sla"] += 1
                    else:
                        periodo["fora_sla"] += 1
            if _acao_esta_aberta_em(acao, periodo["fim"]):
                periodo["abertas"] += 1
                if acao.prazo and acao.prazo < periodo["fim"]:
                    periodo["vencidas"] += 1

        if periodo["fechos_com_tempo"]:
            periodo["tempo_medio_fecho"] = round(periodo["dias_fecho_total"] / periodo["fechos_com_tempo"], 1)
            periodo["taxa_sla"] = round((periodo["dentro_sla"] / periodo["fechos_com_tempo"]) * 100, 1)
    return periodos


def _construir_snapshot_periodo(*, acoes, inicio, fim):
    novas = 0
    concluidas = 0
    abertas = 0
    vencidas = 0
    dentro_sla = 0
    fora_sla = 0
    dias_fecho_total = 0.0
    fechos_com_tempo = 0

    for acao in acoes:
        criado_data = acao.criado_em.date()
        concluida_data = getattr(acao, "concluida_em", None)
        if inicio <= criado_data <= fim:
            novas += 1
        if concluida_data and inicio <= concluida_data <= fim:
            concluidas += 1
            dias_fecho = calcular_dias_fecho_acao(acao)
            if dias_fecho is not None:
                dias_fecho_total += dias_fecho
                fechos_com_tempo += 1
                if dias_fecho <= obter_sla_dias_por_prioridade(getattr(acao, "prioridade", "media")):
                    dentro_sla += 1
                else:
                    fora_sla += 1
        if _acao_esta_aberta_em(acao, fim):
            abertas += 1
            if acao.prazo and acao.prazo < fim:
                vencidas += 1

    return {
        "inicio": inicio,
        "fim": fim,
        "novas": novas,
        "concluidas": concluidas,
        "abertas": abertas,
        "vencidas": vencidas,
        "taxa_sla": round((dentro_sla / fechos_com_tempo) * 100, 1) if fechos_com_tempo else 0.0,
        "tempo_medio_fecho": round(dias_fecho_total / fechos_com_tempo, 1) if fechos_com_tempo else 0.0,
    }


def _selecionar_benchmark(itens, *, modo="melhor"):
    itens_validos = [item for item in itens if item.get("total", 0) > 0]
    if not itens_validos:
        return None
    if modo == "melhor":
        return sorted(
            itens_validos,
            key=lambda row: (
                row["vencidas"],
                -row["taxa_sla"],
                -row["taxa_fecho"],
                row["tempo_medio_fecho"],
                -row["total"],
                row["nome"],
            ),
        )[0]
    return sorted(
        itens_validos,
        key=lambda row: (
            -row["vencidas"],
            -row["abertas"],
            row["taxa_sla"],
            -row["tempo_medio_fecho"],
            -row["total"],
            row["nome"],
        ),
    )[0]


def _agrupar_acoes_por_carga(*, acoes, agrupador, nomeador, referencia, score_config):
    grupos = {}
    pesos = score_config["pesos"]
    thresholds = score_config["thresholds"]
    historico_index = score_config.get("historico_index", {})
    for acao in acoes:
        chave = agrupador(acao)
        nome = nomeador(acao)
        item = grupos.setdefault(
            chave,
            {
                "chave": chave,
                "nome": nome,
                "abertas": 0,
                "vencidas": 0,
                "criticas": 0,
                "alta": 0,
                "vence_7d": 0,
                "score": 0.0,
                "score_ajustado": 0.0,
                "risco": "baixo",
                "taxa_sla_historica": 0.0,
                "taxa_fecho_historica": 0.0,
                "tempo_medio_fecho_historico": 0.0,
                "historico_total": 0,
                "penalizacao_historica": 0.0,
            },
        )
        item["abertas"] += 1
        prioridade = getattr(acao, "prioridade", "media")
        if prioridade == "critica":
            item["criticas"] += 1
        if prioridade == "alta":
            item["alta"] += 1
        if acao.prazo:
            dias = (acao.prazo - referencia).days
            if dias < 0:
                item["vencidas"] += 1
            elif dias <= 7:
                item["vence_7d"] += 1

    for item in grupos.values():
        base_score = (
            (item["vencidas"] * pesos["vencidas"]) +
            (item["criticas"] * pesos["criticas"]) +
            (item["alta"] * pesos["altas"]) +
            (item["vence_7d"] * pesos["vence_7d"]) +
            (item["abertas"] * pesos["abertas"])
        )
        historico = historico_index.get(item["chave"], {})
        item["historico_total"] = int(historico.get("total", 0) or 0)
        item["taxa_sla_historica"] = float(historico.get("taxa_sla", 0.0) or 0.0)
        item["taxa_fecho_historica"] = float(historico.get("taxa_fecho", 0.0) or 0.0)
        item["tempo_medio_fecho_historico"] = float(historico.get("tempo_medio_fecho", 0.0) or 0.0)

        penalizacao = 0.0
        if item["historico_total"] >= 3:
            penalizacao += max(0.0, (80.0 - item["taxa_sla_historica"]) / 12.0)
            penalizacao += max(0.0, (65.0 - item["taxa_fecho_historica"]) / 20.0)
            penalizacao += max(0.0, (item["tempo_medio_fecho_historico"] - 10.0) / 10.0)

        score_ajustado = base_score + penalizacao
        item["score"] = round(base_score, 1)
        item["penalizacao_historica"] = round(penalizacao, 1)
        item["score_ajustado"] = round(score_ajustado, 1)
        if score_ajustado >= thresholds["alto"] or item["vencidas"] >= 3:
            item["risco"] = "alto"
        elif score_ajustado >= thresholds["medio"] or item["vence_7d"] >= 2:
            item["risco"] = "medio"
        else:
            item["risco"] = "baixo"
    return sorted(
        grupos.values(),
        key=lambda row: (-row["score_ajustado"], -row["vencidas"], -row["criticas"], -row["abertas"], row["nome"]),
    )


def _construir_indice_historico_grupo(*, acoes, referencia, agrupador, nomeador):
    mapa = {}
    for acao in acoes:
        chave = agrupador(acao)
        tipo = "corretivas" if isinstance(acao, AcaoCorretiva) else "preventivas"
        item = mapa.setdefault(chave, _novo_item_eficacia(nomeador(acao)))
        item["chave"] = chave
        _aplicar_acao_eficacia(
            mapa=mapa,
            chave=chave,
            nome=nomeador(acao),
            acao=acao,
            tipo=tipo,
            referencia=referencia,
        )
    linhas = _finalizar_itens_eficacia(mapa.values())
    return {item.get("chave"): item for item in linhas}


def _construir_drilldown(*, acoes, referencia, projeto_id=None, responsavel_id=None):
    projeto_id = str(projeto_id or "").strip()
    responsavel_id = str(responsavel_id or "").strip()
    projeto_choices = {}
    responsavel_choices = {}

    for acao in acoes:
        if getattr(acao, "projeto_id", None):
            projeto_choices[str(acao.projeto_id)] = getattr(acao.projeto, "nome", "Sem projeto")
        if getattr(acao, "responsavel_id", None):
            responsavel_choices[str(acao.responsavel_id)] = getattr(acao.responsavel, "nome", "Sem responsável")

    filtradas = list(acoes)
    titulo_partes = []
    if projeto_id:
        filtradas = [acao for acao in filtradas if str(getattr(acao, "projeto_id", "")) == projeto_id]
        titulo_partes.append(projeto_choices.get(projeto_id, "Projeto selecionado"))
    if responsavel_id:
        filtradas = [acao for acao in filtradas if str(getattr(acao, "responsavel_id", "")) == responsavel_id]
        titulo_partes.append(responsavel_choices.get(responsavel_id, "Responsável selecionado"))

    abertas = [acao for acao in filtradas if getattr(acao, "status", None) not in ["concluida", "cancelada"]]
    concluidas = [acao for acao in filtradas if getattr(acao, "status", None) == "concluida"]
    vencidas = [acao for acao in abertas if getattr(acao, "prazo", None) and acao.prazo < referencia]
    vence_7d = [acao for acao in abertas if getattr(acao, "prazo", None) and 0 <= (acao.prazo - referencia).days <= 7]
    fechos_validos = [calcular_dias_fecho_acao(acao) for acao in concluidas]
    fechos_validos = [dias for dias in fechos_validos if dias is not None]
    dentro_sla = [
        acao for acao in concluidas
        if (calcular_dias_fecho_acao(acao) is not None and calcular_dias_fecho_acao(acao) <= obter_sla_dias_por_prioridade(getattr(acao, "prioridade", "media")))
    ]
    taxa_sla = round((len(dentro_sla) / len(fechos_validos)) * 100, 1) if fechos_validos else 0.0
    tempo_medio = round(sum(fechos_validos) / len(fechos_validos), 1) if fechos_validos else 0.0
    itens_brutos = sorted(
        filtradas,
        key=lambda acao: (
            getattr(acao, "status", "") == "concluida",
            getattr(acao, "prazo", None) or date.max,
            -getattr(acao, "criado_em", timezone.now()).timestamp(),
        ),
    )[:10]
    itens = [
        {
            "id": item.pk,
            "tipo_codigo": "corretiva" if isinstance(item, AcaoCorretiva) else "preventiva",
            "titulo": item.titulo,
            "tipo": "Ação corretiva" if isinstance(item, AcaoCorretiva) else "Ação preventiva",
            "projeto": getattr(getattr(item, "projeto", None), "nome", "Sem projeto"),
            "responsavel": getattr(getattr(item, "responsavel", None), "nome", "Sem responsável"),
            "prioridade": item.get_prioridade_display(),
            "status": item.get_status_display(),
            "prazo": getattr(item, "prazo", None),
            "concluida_em": getattr(item, "concluida_em", None),
        }
        for item in itens_brutos
    ]

    return {
        "titulo": " / ".join(titulo_partes) if titulo_partes else "Visão global",
        "projeto_id": projeto_id,
        "responsavel_id": responsavel_id,
        "projeto_choices": [{"id": key, "nome": value} for key, value in sorted(projeto_choices.items(), key=lambda item: item[1])],
        "responsavel_choices": [{"id": key, "nome": value} for key, value in sorted(responsavel_choices.items(), key=lambda item: item[1])],
        "resumo": {
            "total": len(filtradas),
            "abertas": len(abertas),
            "concluidas": len(concluidas),
            "vencidas": len(vencidas),
            "vence_7d": len(vence_7d),
            "taxa_sla": taxa_sla,
            "tempo_medio_fecho": tempo_medio,
        },
        "itens": itens,
    }


def _aplicar_acao_eficacia(*, mapa, chave, nome, acao, tipo, referencia):
    item = mapa.setdefault(chave, _novo_item_eficacia(nome))
    item["chave"] = chave
    item["nome"] = nome or item["nome"]
    item["total"] += 1
    item[tipo] += 1
    item["evidencias"] += int(getattr(acao, "total_evidencias", 0) or 0)
    sla_dias = obter_sla_dias_por_prioridade(getattr(acao, "prioridade", "media"))
    if acao.status == "concluida":
        item["concluidas"] += 1
        dias_fecho = calcular_dias_fecho_acao(acao)
        if dias_fecho is not None:
            item["dias_fecho_total"] += dias_fecho
            item["fechos_com_tempo"] += 1
            if dias_fecho <= sla_dias:
                item["dentro_sla"] += 1
            else:
                item["fora_sla"] += 1
    elif acao.status != "cancelada":
        item["abertas"] += 1
        if acao.prazo and acao.prazo < referencia:
            item["vencidas"] += 1


def _finalizar_itens_eficacia(itens):
    linhas = []
    for item in itens:
        total = int(item["total"] or 0)
        item["taxa_fecho"] = round((item["concluidas"] / total) * 100, 1) if total else 0.0
        fechos_com_tempo = int(item["fechos_com_tempo"] or 0)
        item["tempo_medio_fecho"] = round((item["dias_fecho_total"] / fechos_com_tempo), 1) if fechos_com_tempo else 0.0
        item["taxa_sla"] = round((item["dentro_sla"] / fechos_com_tempo) * 100, 1) if fechos_com_tempo else 0.0
        linhas.append(item)
    linhas.sort(key=lambda row: (-row["vencidas"], -row["abertas"], row["taxa_sla"], -row["total"], row["nome"]))
    return linhas


def construir_dashboard_eficacia_compliance(
    *,
    empresa,
    referencia=None,
    projeto_id=None,
    responsavel_id=None,
    janela_dias=None,
):
    referencia = referencia or timezone.localdate()
    score_config = normalizar_compliance_score_config(
        getattr(empresa, "compliance_score_config", {})
    )
    corretivas = list(
        AcaoCorretiva.objects.filter(empresa=empresa)
        .select_related("responsavel", "projeto")
        .annotate(total_evidencias=Count("evidencias", distinct=True))
    )
    preventivas = list(
        AcaoPreventiva.objects.filter(empresa=empresa)
        .select_related("responsavel", "projeto")
        .annotate(total_evidencias=Count("evidencias", distinct=True))
    )
    todas_acoes = corretivas + preventivas
    inicio_janela = None
    if janela_dias:
        inicio_janela = referencia - timedelta(days=max(int(janela_dias) - 1, 0))
        corretivas = [acao for acao in corretivas if _acao_relevante_na_janela(acao, inicio_janela, referencia)]
        preventivas = [acao for acao in preventivas if _acao_relevante_na_janela(acao, inicio_janela, referencia)]

    responsaveis = {}
    equipas = {}
    projetos = {}
    meses = {}

    for acao in corretivas:
        _aplicar_acao_eficacia(
            mapa=responsaveis,
            chave=acao.responsavel_id or "sem-responsavel",
            nome=getattr(acao.responsavel, "nome", "Sem responsável"),
            acao=acao,
            tipo="corretivas",
            referencia=referencia,
        )
        _aplicar_acao_eficacia(
            mapa=projetos,
            chave=acao.projeto_id or "sem-projeto",
            nome=getattr(acao.projeto, "nome", "Sem projeto"),
            acao=acao,
            tipo="corretivas",
            referencia=referencia,
        )
        _aplicar_acao_eficacia(
            mapa=equipas,
            chave=getattr(getattr(acao, "responsavel", None), "funcao", None) or "sem-funcao",
            nome=_obter_nome_equipa_responsavel(getattr(acao, "responsavel", None)),
            acao=acao,
            tipo="corretivas",
            referencia=referencia,
        )
        chave_mes = acao.criado_em.strftime("%m/%Y")
        bucket = meses.setdefault(chave_mes, {"mes": chave_mes, "novas": 0, "concluidas": 0})
        bucket["novas"] += 1
        if acao.concluida_em:
            chave_fecho = acao.concluida_em.strftime("%m/%Y")
            bucket_fecho = meses.setdefault(chave_fecho, {"mes": chave_fecho, "novas": 0, "concluidas": 0})
            bucket_fecho["concluidas"] += 1

    for acao in preventivas:
        _aplicar_acao_eficacia(
            mapa=responsaveis,
            chave=acao.responsavel_id or "sem-responsavel",
            nome=getattr(acao.responsavel, "nome", "Sem responsável"),
            acao=acao,
            tipo="preventivas",
            referencia=referencia,
        )
        _aplicar_acao_eficacia(
            mapa=projetos,
            chave=acao.projeto_id or "sem-projeto",
            nome=getattr(acao.projeto, "nome", "Sem projeto"),
            acao=acao,
            tipo="preventivas",
            referencia=referencia,
        )
        _aplicar_acao_eficacia(
            mapa=equipas,
            chave=getattr(getattr(acao, "responsavel", None), "funcao", None) or "sem-funcao",
            nome=_obter_nome_equipa_responsavel(getattr(acao, "responsavel", None)),
            acao=acao,
            tipo="preventivas",
            referencia=referencia,
        )
        chave_mes = acao.criado_em.strftime("%m/%Y")
        bucket = meses.setdefault(chave_mes, {"mes": chave_mes, "novas": 0, "concluidas": 0})
        bucket["novas"] += 1
        if acao.concluida_em:
            chave_fecho = acao.concluida_em.strftime("%m/%Y")
            bucket_fecho = meses.setdefault(chave_fecho, {"mes": chave_fecho, "novas": 0, "concluidas": 0})
            bucket_fecho["concluidas"] += 1

    responsaveis_linhas = _finalizar_itens_eficacia(responsaveis.values())
    equipas_linhas = _finalizar_itens_eficacia(equipas.values())
    projetos_linhas = _finalizar_itens_eficacia(projetos.values())

    total_acoes = len(corretivas) + len(preventivas)
    total_concluidas = sum(item["concluidas"] for item in responsaveis_linhas)
    total_abertas = sum(item["abertas"] for item in responsaveis_linhas)
    total_vencidas = sum(item["vencidas"] for item in responsaveis_linhas)
    taxa_global = round((total_concluidas / total_acoes) * 100, 1) if total_acoes else 0.0

    tendencia = sorted(meses.values(), key=lambda row: (int(row["mes"][3:]), int(row["mes"][:2])))
    tendencia = tendencia[-6:]
    historico = _construir_historico_compliance(acoes=corretivas + preventivas, referencia=referencia)
    tendencia_trimestral = _construir_historico_trimestral_compliance(acoes=corretivas + preventivas, referencia=referencia)
    periodo_atual = historico[-1] if historico else None
    periodo_anterior = historico[-2] if len(historico) > 1 else None
    benchmark = {
        "melhor_responsavel": _selecionar_benchmark(responsaveis_linhas, modo="melhor"),
        "responsavel_maior_risco": _selecionar_benchmark(responsaveis_linhas, modo="risco"),
        "melhor_equipa": _selecionar_benchmark(equipas_linhas, modo="melhor"),
        "equipa_maior_risco": _selecionar_benchmark(equipas_linhas, modo="risco"),
    }
    abertas_gerais = [
        acao for acao in (corretivas + preventivas)
        if getattr(acao, "status", None) not in ["concluida", "cancelada"]
    ]
    historico_responsaveis = _construir_indice_historico_grupo(
        acoes=todas_acoes,
        referencia=referencia,
        agrupador=lambda acao: getattr(acao, "responsavel_id", None) or "sem-responsavel",
        nomeador=lambda acao: getattr(getattr(acao, "responsavel", None), "nome", "Sem responsável"),
    )
    historico_projetos = _construir_indice_historico_grupo(
        acoes=todas_acoes,
        referencia=referencia,
        agrupador=lambda acao: getattr(acao, "projeto_id", None) or "sem-projeto",
        nomeador=lambda acao: getattr(getattr(acao, "projeto", None), "nome", "Sem projeto"),
    )
    previsao_incumprimento = {
        "responsaveis": _agrupar_acoes_por_carga(
            acoes=abertas_gerais,
            agrupador=lambda acao: getattr(acao, "responsavel_id", None) or "sem-responsavel",
            nomeador=lambda acao: getattr(getattr(acao, "responsavel", None), "nome", "Sem responsável"),
            referencia=referencia,
            score_config={**score_config, "historico_index": historico_responsaveis},
        )[:6],
        "projetos": _agrupar_acoes_por_carga(
            acoes=abertas_gerais,
            agrupador=lambda acao: getattr(acao, "projeto_id", None) or "sem-projeto",
            nomeador=lambda acao: getattr(getattr(acao, "projeto", None), "nome", "Sem projeto"),
            referencia=referencia,
            score_config={**score_config, "historico_index": historico_projetos},
        )[:6],
    }
    drilldown = _construir_drilldown(
        acoes=corretivas + preventivas,
        referencia=referencia,
        projeto_id=projeto_id,
        responsavel_id=responsavel_id,
    )
    snapshots = {
        "janela_dias": int(janela_dias or 0),
        "atual": None,
        "anterior": None,
        "delta_abertas": 0,
        "delta_concluidas": 0,
        "delta_vencidas": 0,
        "delta_sla": 0.0,
        "delta_tempo_medio": 0.0,
    }
    if inicio_janela:
        janela_total = max(int(janela_dias or 0), 1)
        fim_anterior = inicio_janela - timedelta(days=1)
        inicio_anterior = fim_anterior - timedelta(days=janela_total - 1)
        snapshot_atual = _construir_snapshot_periodo(acoes=todas_acoes, inicio=inicio_janela, fim=referencia)
        snapshot_anterior = _construir_snapshot_periodo(acoes=todas_acoes, inicio=inicio_anterior, fim=fim_anterior)
        snapshots = {
            "janela_dias": janela_total,
            "atual": snapshot_atual,
            "anterior": snapshot_anterior,
            "delta_abertas": snapshot_atual["abertas"] - snapshot_anterior["abertas"],
            "delta_concluidas": snapshot_atual["concluidas"] - snapshot_anterior["concluidas"],
            "delta_vencidas": snapshot_atual["vencidas"] - snapshot_anterior["vencidas"],
            "delta_sla": round(snapshot_atual["taxa_sla"] - snapshot_anterior["taxa_sla"], 1),
            "delta_tempo_medio": round(snapshot_atual["tempo_medio_fecho"] - snapshot_anterior["tempo_medio_fecho"], 1),
        }

    return {
        "resumo": {
            "total_acoes": total_acoes,
            "total_concluidas": total_concluidas,
            "total_abertas": total_abertas,
            "total_vencidas": total_vencidas,
            "taxa_global_fecho": taxa_global,
            "tempo_medio_fecho_global": round(
                sum(item["dias_fecho_total"] for item in responsaveis_linhas) /
                max(sum(item["fechos_com_tempo"] for item in responsaveis_linhas), 1),
                1,
            ) if total_concluidas else 0.0,
            "taxa_sla_global": round(
                (sum(item["dentro_sla"] for item in responsaveis_linhas) /
                 max(sum(item["fechos_com_tempo"] for item in responsaveis_linhas), 1)) * 100,
                1,
            ) if total_concluidas else 0.0,
            "responsaveis_criticos": sum(1 for item in responsaveis_linhas if item["vencidas"] > 0 or item["abertas"] >= 3),
            "projetos_em_risco": sum(1 for item in projetos_linhas if item["vencidas"] > 0 or item["abertas"] >= 3),
            "equipas_em_risco": sum(1 for item in equipas_linhas if item["vencidas"] > 0 or item["abertas"] >= 3),
        },
        "responsaveis": responsaveis_linhas[:8],
        "equipas": equipas_linhas[:8],
        "projetos": projetos_linhas[:8],
        "tendencia": tendencia,
        "historico": historico,
        "tendencia_trimestral": tendencia_trimestral,
        "comparativos": {
            "periodo_atual": periodo_atual,
            "periodo_anterior": periodo_anterior,
            "delta_abertas": (periodo_atual["abertas"] - periodo_anterior["abertas"]) if periodo_atual and periodo_anterior else 0,
            "delta_concluidas": (periodo_atual["concluidas"] - periodo_anterior["concluidas"]) if periodo_atual and periodo_anterior else 0,
            "delta_vencidas": (periodo_atual["vencidas"] - periodo_anterior["vencidas"]) if periodo_atual and periodo_anterior else 0,
            "delta_sla": round((periodo_atual["taxa_sla"] - periodo_anterior["taxa_sla"]), 1) if periodo_atual and periodo_anterior else 0.0,
            "delta_tempo_medio": round((periodo_atual["tempo_medio_fecho"] - periodo_anterior["tempo_medio_fecho"]), 1) if periodo_atual and periodo_anterior else 0.0,
        },
        "benchmark": benchmark,
        "previsao_incumprimento": previsao_incumprimento,
        "drilldown": drilldown,
        "snapshots": snapshots,
        "score_config": score_config,
        "janela_dias": int(janela_dias or 0),
        "inicio_janela": inicio_janela,
        "referencia": referencia,
    }


def sincronizar_alertas_automaticos_compliance(*, empresa, referencia=None):
    referencia = referencia or timezone.localdate()
    alertas_criticos_ids = []
    alertas_preventivos_ids = []

    acoes_abertas = list(
        AcaoCorretiva.objects.filter(empresa=empresa)
        .exclude(status__in=["concluida", "cancelada"])
        .select_related("projeto", "responsavel")
    ) + list(
        AcaoPreventiva.objects.filter(empresa=empresa)
        .exclude(status__in=["concluida", "cancelada"])
        .select_related("projeto", "responsavel")
    )

    for acao in acoes_abertas:
        if not acao.prazo:
            continue
        tipo_acao = "corretiva" if isinstance(acao, AcaoCorretiva) else "preventiva"
        origem_url = "/app/gestao/compliance-seguranca/"
        prioridade_notificacao = "alta" if getattr(acao, "prioridade", "media") in ["alta", "critica"] else getattr(acao, "prioridade", "media")
        prazo_datetime = timezone.make_aware(datetime.combine(acao.prazo, time.min))

        if getattr(acao, "prioridade", None) == "critica" and acao.prazo < referencia:
            titulo = f"Compliance crítico vencido: {acao.titulo}"
            detalhes = (
                f"Ação {tipo_acao} crítica vencida desde {acao.prazo.strftime('%d/%m/%Y')}. "
                f"Projeto: {getattr(acao.projeto, 'nome', 'Sem projeto')}. "
                f"Responsável: {getattr(acao.responsavel, 'nome', 'Sem responsável')}."
            )
            notificacao, _ = NotificacaoGestao.objects.update_or_create(
                empresa=empresa,
                tipo="compliance_critico",
                titulo=titulo,
                origem_url=origem_url,
                defaults={
                    "prioridade": "alta",
                    "estado": "aberta",
                    "responsavel": getattr(acao, "responsavel", None),
                    "prazo": prazo_datetime,
                    "detalhes": detalhes,
                },
            )
            alertas_criticos_ids.append(notificacao.pk)
            continue

        dias_restantes = (acao.prazo - referencia).days
        janela_alerta = obter_janela_alerta_preventivo(getattr(acao, "prioridade", "media"))
        if 0 <= dias_restantes <= janela_alerta:
            titulo = f"Compliance a vencer: {acao.titulo}"
            detalhes = (
                f"Ação {tipo_acao} {getattr(acao, 'get_prioridade_display', lambda: 'Média')().lower()} "
                f"vence em {dias_restantes} dia(s), a {acao.prazo.strftime('%d/%m/%Y')}. "
                f"Projeto: {getattr(acao.projeto, 'nome', 'Sem projeto')}. "
                f"Responsável: {getattr(acao.responsavel, 'nome', 'Sem responsável')}."
            )
            notificacao, _ = NotificacaoGestao.objects.update_or_create(
                empresa=empresa,
                tipo="compliance_preventivo",
                titulo=titulo,
                origem_url=origem_url,
                defaults={
                    "prioridade": prioridade_notificacao,
                    "estado": "aberta",
                    "responsavel": getattr(acao, "responsavel", None),
                    "prazo": prazo_datetime,
                    "detalhes": detalhes,
                },
            )
            alertas_preventivos_ids.append(notificacao.pk)

    for tipo, ativos in [("compliance_critico", alertas_criticos_ids), ("compliance_preventivo", alertas_preventivos_ids)]:
        queryset = NotificacaoGestao.objects.filter(empresa=empresa, tipo=tipo).exclude(estado="resolvida")
        if ativos:
            queryset = queryset.exclude(pk__in=ativos)
        queryset.update(estado="resolvida", atualizado_em=timezone.now())

    criticos = list(
        NotificacaoGestao.objects.filter(empresa=empresa, tipo="compliance_critico", estado="aberta")
        .select_related("responsavel")
        .order_by("prazo", "-criado_em")[:8]
    )
    preventivos = list(
        NotificacaoGestao.objects.filter(empresa=empresa, tipo="compliance_preventivo", estado="aberta")
        .select_related("responsavel")
        .order_by("prazo", "-criado_em")[:8]
    )
    return {
        "criticos": criticos,
        "preventivos": preventivos,
    }
