import calendar
from datetime import date, datetime, timedelta


def criar_planeamento_turno(*, form, empresa):
    obj = form.save(commit=False)
    obj.empresa = empresa
    obj.save()
    return obj


def atualizar_planeamento_turno(*, form):
    return form.save()


def apagar_planeamento_turno(*, obj):
    obj.delete()


def resolver_data_referencia_calendario(valor=None):
    if isinstance(valor, date):
        return valor
    if valor:
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()


def _iterar_datas_intervalo(inicio, fim):
    atual = inicio
    while atual <= fim:
        yield atual
        atual += timedelta(days=1)


def _mapear_itens_por_dia(items, *, inicio, fim):
    itens_por_dia = {}
    for item in items:
        item_inicio = item.data_inicio
        item_fim = item.data_fim or item.data_inicio
        if item_fim < inicio or item_inicio > fim:
            continue
        faixa_inicio = max(item_inicio, inicio)
        faixa_fim = min(item_fim, fim)
        for dia in _iterar_datas_intervalo(faixa_inicio, faixa_fim):
            itens_por_dia.setdefault(dia, []).append(item)
    return itens_por_dia


def construir_calendario_semanal_planeamento(*, items, conflitos, referencia=None):
    referencia = resolver_data_referencia_calendario(referencia)
    inicio_semana = referencia - timedelta(days=referencia.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    dias = [inicio_semana + timedelta(days=offset) for offset in range(7)]
    itens_por_dia = _mapear_itens_por_dia(items, inicio=inicio_semana, fim=fim_semana)

    conflito_ids = set()
    for conflito in conflitos:
        conflito_ids.add(str(conflito["a"].id))
        conflito_ids.add(str(conflito["b"].id))

    turno_choices = [
        ("manha", "Manhã"),
        ("tarde", "Tarde"),
        ("noite", "Noite"),
        ("extra", "Extra"),
        ("extra_manha", "Extra Manhã"),
        ("extra_tarde", "Extra Tarde"),
        ("extra_noite", "Extra Noite"),
    ]
    linhas = []
    for turno_valor, turno_label in turno_choices:
        celulas = []
        for dia in dias:
            dia_items = [item for item in itens_por_dia.get(dia, []) if item.turno == turno_valor]
            celulas.append(
                {
                    "data": dia,
                    "items": dia_items,
                    "total": len(dia_items),
                    "confirmados": sum(1 for item in dia_items if item.estado == "confirmado"),
                    "conflitos": sum(1 for item in dia_items if str(item.id) in conflito_ids),
                }
            )
        linhas.append({"turno": turno_label, "turno_valor": turno_valor, "celulas": celulas})

    return {
        "modo": "semanal",
        "referencia": referencia,
        "inicio": inicio_semana,
        "fim": fim_semana,
        "dias": dias,
        "linhas": linhas,
    }


def construir_calendario_mensal_planeamento(*, items, conflitos, referencia=None):
    referencia = resolver_data_referencia_calendario(referencia)
    primeiro_dia = referencia.replace(day=1)
    ultimo_dia = referencia.replace(day=calendar.monthrange(referencia.year, referencia.month)[1])
    inicio_grade = primeiro_dia - timedelta(days=primeiro_dia.weekday())
    fim_grade = ultimo_dia + timedelta(days=(6 - ultimo_dia.weekday()))
    itens_por_dia = _mapear_itens_por_dia(items, inicio=inicio_grade, fim=fim_grade)

    conflito_ids = set()
    for conflito in conflitos:
        conflito_ids.add(str(conflito["a"].id))
        conflito_ids.add(str(conflito["b"].id))

    semanas = []
    semana_atual = []
    for dia in _iterar_datas_intervalo(inicio_grade, fim_grade):
        dia_items = itens_por_dia.get(dia, [])
        semana_atual.append(
            {
                "data": dia,
                "items": dia_items,
                "total": len(dia_items),
                "confirmados": sum(1 for item in dia_items if item.estado == "confirmado"),
                "conflitos": sum(1 for item in dia_items if str(item.id) in conflito_ids),
                "fora_mes": dia.month != referencia.month,
            }
        )
        if len(semana_atual) == 7:
            semanas.append(semana_atual)
            semana_atual = []

    return {
        "modo": "mensal",
        "referencia": referencia,
        "inicio": primeiro_dia,
        "fim": ultimo_dia,
        "semanas": semanas,
    }
