import calendar
from datetime import date, timedelta

from django.shortcuts import get_object_or_404
from django.db.models import Case, F, FloatField, Q, Sum, Value, When
from django.utils import timezone

from projetos.models import AssiduidadeRegisto, PlaneamentoTurno, RegistoDiarioEmpregado


def _normalizar_int(valor, *, minimo=None, maximo=None, default=None):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return default
    if minimo is not None and numero < minimo:
        return default
    if maximo is not None and numero > maximo:
        return default
    return numero


def _aplicar_filtro_periodo_assiduidade(queryset, *, mes="", ano=""):
    mes_int = _normalizar_int(mes, minimo=1, maximo=12)
    ano_int = _normalizar_int(ano, minimo=2000, maximo=2100)

    if mes_int and ano_int:
        inicio = date(ano_int, mes_int, 1)
        _, ultimo_dia = calendar.monthrange(ano_int, mes_int)
        fim = date(ano_int, mes_int, ultimo_dia)
    elif ano_int:
        inicio = date(ano_int, 1, 1)
        fim = date(ano_int, 12, 31)
    elif mes_int:
        ano_atual = timezone.localdate().year
        inicio = date(ano_atual, mes_int, 1)
        _, ultimo_dia = calendar.monthrange(ano_atual, mes_int)
        fim = date(ano_atual, mes_int, ultimo_dia)
    else:
        return queryset

    return queryset.filter(data_inicio__lte=fim).filter(
        Q(data_fim__isnull=True, data_inicio__gte=inicio) | Q(data_fim__gte=inicio)
    )


def listar_assiduidade_empresa(empresa):
    return (
        AssiduidadeRegisto.objects.filter(empresa=empresa)
        .select_related("empregado", "projeto")
        .order_by("-data_inicio", "-atualizado_em")
    )


def listar_assiduidade_empresa_filtro(empresa, *, estado="", tipo="", empregado_id="", mes="", ano=""):
    queryset = AssiduidadeRegisto.objects.filter(empresa=empresa).select_related("empregado", "projeto")
    if estado:
        queryset = queryset.filter(estado=estado)
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if empregado_id:
        queryset = queryset.filter(empregado_id=empregado_id)
    queryset = _aplicar_filtro_periodo_assiduidade(queryset, mes=mes, ano=ano)
    return queryset.order_by("-data_inicio", "-atualizado_em")


def obter_assiduidade_empresa(*, pk, empresa):
    return get_object_or_404(
        AssiduidadeRegisto.objects.select_related("empregado", "projeto"),
        pk=pk,
        empresa=empresa,
    )


def resumo_horas_por_empregado(empresa):
    return (
        AssiduidadeRegisto.objects.filter(empresa=empresa)
        .values(nome=F("empregado__nome"))
        .annotate(
            horas_aprovadas=Sum(
                Case(
                    When(estado="aprovado", then=F("horas")),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
            horas_extras_aprovadas=Sum(
                Case(
                    When(estado="aprovado", tipo="hora_extra", then=F("horas")),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
            faltas=Sum(
                Case(
                    When(tipo="falta", then=Value(1.0)),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
        )
        .order_by("nome")
    )


def saldo_mensal_por_empregado(empresa, *, mes, ano):
    return (
        _aplicar_filtro_periodo_assiduidade(
            AssiduidadeRegisto.objects.filter(empresa=empresa, estado="aprovado"),
            mes=mes,
            ano=ano,
        )
        .values(nome=F("empregado__nome"))
        .annotate(
            horas_presenca=Sum(
                Case(
                    When(tipo="presenca", then=F("horas")),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
            horas_extras=Sum(
                Case(
                    When(tipo="hora_extra", then=F("horas")),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
            horas_falta=Sum(
                Case(
                    When(tipo="falta", then=F("horas")),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
        )
        .order_by("nome")
    )


def listar_assiduidade_empregado(empresa, empregado, *, ano=None):
    queryset = (
        AssiduidadeRegisto.objects.filter(empresa=empresa, empregado=empregado)
        .select_related("projeto")
        .order_by("-data_inicio", "-atualizado_em")
    )
    if ano:
        inicio_ano = date(int(ano), 1, 1)
        fim_ano = date(int(ano), 12, 31)
        queryset = queryset.filter(data_inicio__lte=fim_ano).filter(
            Q(data_fim__isnull=True, data_inicio__gte=inicio_ano) | Q(data_fim__gte=inicio_ano)
        )
    return queryset


def _iterar_datas_intervalo(data_inicio, data_fim):
    atual = data_inicio
    limite = data_fim or data_inicio
    while atual <= limite:
        yield atual
        atual += timedelta(days=1)


def construir_contexto_calendario_turnos_empregado(empregado, *, ano):
    empresa = empregado.empresa
    hoje = timezone.localdate()

    registos = (
        RegistoDiarioEmpregado.objects.filter(
            empresa=empresa,
            empregado=empregado,
            data__year=ano,
        )
        .select_related("projeto", "furo", "planeamento_turno")
        .order_by("-data", "-criado_em")
    )
    planeamentos = (
        PlaneamentoTurno.objects.filter(
            empresa=empresa,
            empregado=empregado,
        )
        .select_related("projeto", "furo", "maquina")
        .order_by("data_inicio", "hora_inicio", "criado_em")
    )
    assiduidades = listar_assiduidade_empregado(empresa, empregado, ano=ano)

    registos_por_data = {}
    for registo in registos:
        registos_por_data.setdefault(registo.data, registo)

    planeamentos_por_data = {}
    for item in planeamentos:
        data_fim = item.data_fim or item.data_inicio
        if data_fim.year < ano or item.data_inicio.year > ano:
            continue
        for dia in _iterar_datas_intervalo(item.data_inicio, data_fim):
            if dia.year != ano:
                continue
            planeamentos_por_data.setdefault(dia, item)

    assiduidade_por_data = {}
    pedidos_ferias = []
    for item in assiduidades:
        data_fim = item.data_fim or item.data_inicio
        if item.tipo == "ferias":
            pedidos_ferias.append(item)
        for dia in _iterar_datas_intervalo(item.data_inicio, data_fim):
            if dia.year != ano:
                continue
            assiduidade_por_data.setdefault(dia, []).append(item)

    meses = []
    cal = calendar.Calendar(firstweekday=0)
    dias_trabalhados = 0
    dias_planeados = 0
    ferias_pendentes = 0
    ferias_aprovadas = 0

    for mes in range(1, 13):
        semanas = []
        for semana in cal.monthdatescalendar(ano, mes):
            dias_semana = []
            for dia in semana:
                no_mes = dia.month == mes
                registo = registos_por_data.get(dia) if no_mes else None
                planeamento = planeamentos_por_data.get(dia) if no_mes else None
                assiduidades_dia = assiduidade_por_data.get(dia, []) if no_mes else []
                ferias_dia = next((x for x in assiduidades_dia if x.tipo == "ferias"), None)
                worked = registo is not None
                planned = planeamento is not None
                if worked:
                    dias_trabalhados += 1
                elif planned:
                    dias_planeados += 1
                if ferias_dia and ferias_dia.estado == "pendente":
                    ferias_pendentes += 1
                elif ferias_dia and ferias_dia.estado == "aprovado":
                    ferias_aprovadas += 1

                estado_ferias = ferias_dia.estado if ferias_dia else ""
                texto_estado = ""
                if estado_ferias == "pendente":
                    texto_estado = "Férias pendentes"
                elif estado_ferias == "aprovado":
                    texto_estado = "Férias aprovadas"
                elif estado_ferias == "rejeitado":
                    texto_estado = "Férias rejeitadas"
                elif worked:
                    texto_estado = "Registo criado"
                elif planned:
                    texto_estado = "Turno planeado"

                dias_semana.append(
                    {
                        "data": dia,
                        "iso": dia.isoformat(),
                        "dia": dia.day,
                        "no_mes": no_mes,
                        "is_today": dia == hoje,
                        "is_past": dia < hoje,
                        "is_weekend": dia.weekday() >= 5,
                        "worked": worked,
                        "planned": planned,
                        "estado_ferias": estado_ferias,
                        "estado_texto": texto_estado,
                        "selectable": no_mes and dia >= hoje and estado_ferias not in {"pendente", "aprovado"},
                        "registo": registo,
                        "planeamento": planeamento,
                    }
                )
            semanas.append(dias_semana)
        meses.append(
            {
                "numero": mes,
                "nome": calendar.month_name[mes],
                "primeiro_dia": date(ano, mes, 1),
                "semanas": semanas,
            }
        )

    pedidos_ferias = pedidos_ferias[:12]
    return {
        "ano": ano,
        "meses": meses,
        "dias_trabalhados": dias_trabalhados,
        "dias_planeados": dias_planeados,
        "dias_ferias_anuais": empregado.dias_ferias_anuais,
        "dias_ferias_gozados": empregado.dias_ferias_gozados(ano=ano),
        "dias_ferias_disponiveis": empregado.dias_ferias_disponiveis(ano=ano),
        "ferias_pendentes": ferias_pendentes,
        "ferias_aprovadas": ferias_aprovadas,
        "pedidos_ferias": pedidos_ferias,
    }


def construir_contexto_calendario_equipa_empresa(empresa, *, ano, mes, empregado_id=""):
    hoje = timezone.localdate()
    try:
        ano = int(ano)
    except (TypeError, ValueError):
        ano = hoje.year
    try:
        mes = int(mes)
    except (TypeError, ValueError):
        mes = hoje.month

    ano = max(2000, min(2100, ano))
    mes = max(1, min(12, mes))

    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = date(ano, mes, calendar.monthrange(ano, mes)[1])

    registos_qs = (
        RegistoDiarioEmpregado.objects.filter(
            empresa=empresa,
            data__gte=primeiro_dia,
            data__lte=ultimo_dia,
        )
        .select_related("empregado", "projeto", "furo", "planeamento_turno", "planeamento_turno__maquina")
        .order_by("data", "empregado__nome", "hora_inicio", "criado_em")
    )
    planeamentos_qs = (
        PlaneamentoTurno.objects.filter(
            empresa=empresa,
            data_inicio__lte=ultimo_dia,
        )
        .filter(Q(data_fim__isnull=True, data_inicio__gte=primeiro_dia) | Q(data_fim__gte=primeiro_dia))
        .exclude(estado="cancelado")
        .select_related("empregado", "projeto", "furo", "maquina")
        .order_by("data_inicio", "empregado__nome", "hora_inicio", "criado_em")
    )
    assiduidades_qs = (
        AssiduidadeRegisto.objects.filter(empresa=empresa)
        .filter(
            Q(data_inicio__lte=ultimo_dia)
            & (Q(data_fim__isnull=True, data_inicio__gte=primeiro_dia) | Q(data_fim__gte=primeiro_dia))
        )
        .select_related("empregado", "projeto")
        .order_by("data_inicio", "empregado__nome")
    )

    if empregado_id:
        registos_qs = registos_qs.filter(empregado_id=empregado_id)
        planeamentos_qs = planeamentos_qs.filter(empregado_id=empregado_id)
        assiduidades_qs = assiduidades_qs.filter(empregado_id=empregado_id)

    entradas_por_data = {}
    chaves_registo = set()
    total_turnos = 0
    total_registos = 0
    colaboradores_ids = set()

    for registo in registos_qs:
        turno_label = (
            registo.turno
            or (registo.planeamento_turno.get_turno_display() if registo.planeamento_turno_id else "")
            or "Sem turno"
        )
        horario = ""
        if registo.hora_inicio and registo.hora_fim:
            horario = f"{registo.hora_inicio.strftime('%H:%M')} - {registo.hora_fim.strftime('%H:%M')}"
        elif registo.planeamento_turno_id:
            horario = registo.planeamento_turno.intervalo_horario_display

        chave_registo = (
            registo.data,
            registo.empregado_id,
            turno_label,
            str(registo.hora_inicio or ""),
            str(registo.hora_fim or ""),
        )
        chaves_registo.add(chave_registo)
        entradas_por_data.setdefault(registo.data, []).append(
            {
                "empregado_nome": registo.empregado.nome,
                "turno_label": turno_label,
                "horario": horario or "-",
                "projeto_nome": registo.projeto.nome if registo.projeto_id else "-",
                "furo_nome": registo.furo.nome if registo.furo_id else "-",
                "maquina_nome": (
                    registo.planeamento_turno.maquina.nome
                    if registo.planeamento_turno_id and registo.planeamento_turno.maquina_id
                    else "-"
                ),
                "estado_label": "Registo criado",
                "origem": "registo",
            }
        )
        total_turnos += 1
        total_registos += 1
        colaboradores_ids.add(registo.empregado_id)

    for planeamento in planeamentos_qs:
        turno_label = planeamento.get_turno_display()
        data_fim = planeamento.data_fim or planeamento.data_inicio
        atual = max(planeamento.data_inicio, primeiro_dia)
        limite = min(data_fim, ultimo_dia)
        while atual <= limite:
            chave_planeamento = (
                atual,
                planeamento.empregado_id,
                turno_label,
                str(planeamento.hora_inicio or ""),
                str(planeamento.hora_fim or ""),
            )
            if chave_planeamento not in chaves_registo:
                entradas_por_data.setdefault(atual, []).append(
                    {
                        "empregado_nome": planeamento.empregado.nome if planeamento.empregado_id else "Sem empregado",
                        "turno_label": turno_label,
                        "horario": planeamento.intervalo_horario_display or "-",
                        "projeto_nome": planeamento.projeto.nome if planeamento.projeto_id else "-",
                        "furo_nome": planeamento.furo.nome if planeamento.furo_id else "-",
                        "maquina_nome": planeamento.maquina.nome if planeamento.maquina_id else "-",
                        "estado_label": planeamento.get_estado_display(),
                        "origem": "planeamento",
                    }
                )
                total_turnos += 1
            atual += timedelta(days=1)
        if planeamento.empregado_id:
            colaboradores_ids.add(planeamento.empregado_id)

    ausencias_por_data = {}
    total_ausencias = 0
    for item in assiduidades_qs:
        if item.tipo not in {"ferias", "falta", "baixa"}:
            continue
        data_fim = item.data_fim or item.data_inicio
        atual = max(item.data_inicio, primeiro_dia)
        limite = min(data_fim, ultimo_dia)
        while atual <= limite:
            ausencias_por_data.setdefault(atual, []).append(
                {
                    "empregado_nome": item.empregado.nome,
                    "tipo_label": item.get_tipo_display(),
                    "estado_label": item.get_estado_display(),
                }
            )
            total_ausencias += 1
            atual += timedelta(days=1)

    cal = calendar.Calendar(firstweekday=0)
    semanas = []
    for semana in cal.monthdatescalendar(ano, mes):
        dias_semana = []
        for dia in semana:
            entradas = sorted(
                entradas_por_data.get(dia, []),
                key=lambda row: (row["empregado_nome"].lower(), row["turno_label"].lower(), row["horario"]),
            ) if dia.month == mes else []
            ausencias = sorted(
                ausencias_por_data.get(dia, []),
                key=lambda row: (row["empregado_nome"].lower(), row["tipo_label"].lower()),
            ) if dia.month == mes else []
            dias_semana.append(
                {
                    "data": dia,
                    "dia": dia.day,
                    "iso": dia.isoformat(),
                    "no_mes": dia.month == mes,
                    "is_today": dia == hoje,
                    "entradas": entradas,
                    "ausencias": ausencias,
                    "total_turnos": len(entradas),
                    "total_ausencias": len(ausencias),
                }
            )
        semanas.append(dias_semana)

    if mes == 1:
        mes_anterior, ano_anterior = 12, ano - 1
    else:
        mes_anterior, ano_anterior = mes - 1, ano

    if mes == 12:
        mes_seguinte, ano_seguinte = 1, ano + 1
    else:
        mes_seguinte, ano_seguinte = mes + 1, ano

    return {
        "ano": ano,
        "mes": mes,
        "mes_nome": calendar.month_name[mes],
        "semanas": semanas,
        "total_turnos": total_turnos,
        "total_registos": total_registos,
        "total_ausencias": total_ausencias,
        "total_colaboradores": len(colaboradores_ids),
        "mes_anterior": mes_anterior,
        "ano_anterior": ano_anterior,
        "mes_seguinte": mes_seguinte,
        "ano_seguinte": ano_seguinte,
    }
