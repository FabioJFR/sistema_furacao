from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from projetos.models import Empregados, Furo, Projeto, RegistoDiarioEmpregado


def _filtro_tem_relatorio_tecnico():
    q = Q()
    for campo in [
        "cliente", "sonda", "torre", "bomba_injecao", "bomba_captacao", "estaleiro",
        "numero_sondagem", "numero_relatorio", "furacao_rocha", "furacao_descricao",
        "outros", "notas", "especialista_1", "especialista_2", "especialista_3",
        "especialista_4", "servente_1", "servente_2", "servente_3", "servente_4",
        "turno",
    ]:
        q |= ~Q(**{campo: ""})
    for campo in [
        "inclinacao", "diametro_furo", "no_inicio", "no_final", "avanco_turno",
        "testemunho_recuperado", "percentagem_recuperacao", "furacao_inicio", "furacao_fim",
        "furacao_avanco", "furacao_recuperacao", "manobra_de", "manobra_ate", "reaming_de",
        "reaming_ate", "avaria_de", "avaria_ate", "horas_paragem_de", "horas_paragem_ate",
        "medicao_desvio_de", "medicao_desvio_ate", "cimentacao_de", "cimentacao_ate",
        "lavar_furo_de", "lavar_furo_ate", "polimeros_de", "polimeros_ate",
        "varas_presas_de", "varas_presas_ate", "outros_de", "outros_ate", "entubamento_de",
        "entubamento_ate", "horas_especialista_1", "horas_especialista_2", "horas_especialista_3",
        "horas_especialista_4", "horas_servente_1", "horas_servente_2", "horas_servente_3",
        "horas_servente_4", "bit_novo_de", "bit_novo_ate",
    ]:
        q |= Q(**{f"{campo}__isnull": False})
    q |= ~Q(polimeros=[])
    q |= ~Q(furacoes=[])
    for campo in [
        "manobra", "reaming", "avaria", "relatorio_horas_paragem", "medicao_desvio",
        "cimentacao", "lavar_furo", "varas_presas", "entubamento", "bit_novo",
    ]:
        q |= Q(**{campo: "sim"})
    return q


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def obter_registos_empregado(empregado):
    return (
        empregado.registos_diarios.select_related("projeto", "furo", "planeamento_turno")
        .filter(empresa_id=empregado.empresa_id)
        .order_by("-data", "-criado_em")
    )


def obter_registo_empregado(empregado, pk):
    return get_object_or_404(
        RegistoDiarioEmpregado.objects.select_related("projeto", "furo", "planeamento_turno"),
        pk=pk,
        empregado=empregado,
        empresa_id=empregado.empresa_id,
    )


def obter_registos_admin_filtrados(empresa, filtros):
    empresa_id = _resolver_empresa_id(empresa)
    queryset = (
        RegistoDiarioEmpregado.objects.select_related("empregado", "projeto", "furo", "planeamento_turno")
        .filter(
            empresa_id=empresa_id,
            empregado__empresa_id=empresa_id,
        )
        .order_by("-data", "-criado_em")
    )

    empregado_id = (filtros.get("empregado") or "").strip()
    projeto_id = (filtros.get("projeto") or "").strip()
    furo_id = (filtros.get("furo") or "").strip()
    data_inicio = (filtros.get("data_inicio") or "").strip()
    data_fim = (filtros.get("data_fim") or "").strip()

    if empregado_id:
        queryset = queryset.filter(empregado_id=empregado_id)

    if projeto_id:
        queryset = queryset.filter(projeto_id=projeto_id)

    if furo_id:
        queryset = queryset.filter(furo_id=furo_id)

    if data_inicio:
        data_inicio_parsed = parse_date(data_inicio)
        if data_inicio_parsed:
            queryset = queryset.filter(data__gte=data_inicio_parsed)

    if data_fim:
        data_fim_parsed = parse_date(data_fim)
        if data_fim_parsed:
            queryset = queryset.filter(data__lte=data_fim_parsed)

    totais = queryset.aggregate(
        total_horas=Sum("horas_trabalhadas"),
        total_metros=Sum("metros_furados"),
        total_paragem=Sum("horas_paragem"),
    )

    return {
        "registos": queryset,
        "totais": totais,
        "filtros": {
            "empregado": empregado_id,
            "projeto": projeto_id,
            "furo": furo_id,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
    }


def obter_contexto_filtros_registos_admin(empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return {
        "empregados": Empregados.objects.filter(empresa_id=empresa_id).order_by("nome"),
        "projetos": Projeto.objects.filter(empresa_id=empresa_id).order_by("nome"),
        "furos": Furo.objects.filter(empresa_id=empresa_id).order_by("nome"),
    }


def obter_registo_admin(empresa, pk):
    empresa_id = _resolver_empresa_id(empresa)
    return get_object_or_404(
        RegistoDiarioEmpregado.objects.select_related("empregado", "projeto", "furo", "planeamento_turno"),
        pk=pk,
        empresa_id=empresa_id,
        empregado__empresa_id=empresa_id,
    )


def obter_relatorio_turno_empregado(empregado, pk):
    return get_object_or_404(
        RegistoDiarioEmpregado.objects.select_related("empregado", "projeto", "furo", "planeamento_turno").filter(_filtro_tem_relatorio_tecnico()),
        pk=pk,
        empresa_id=empregado.empresa_id,
        empregado=empregado,
    )


def obter_relatorio_turno_admin(empresa, pk):
    empresa_id = _resolver_empresa_id(empresa)
    return get_object_or_404(
        RegistoDiarioEmpregado.objects.select_related("empregado", "projeto", "furo", "planeamento_turno").filter(_filtro_tem_relatorio_tecnico()),
        pk=pk,
        empresa_id=empresa_id,
        empregado__empresa_id=empresa_id,
    )


def obter_relatorios_turno_empregado(empregado, filtros=None):
    filtros = filtros or {}
    queryset = (
        RegistoDiarioEmpregado.objects.select_related(
            "projeto",
            "furo",
            "planeamento_turno",
            "planeamento_turno__maquina",
            "empregado",
        )
        .filter(
            empresa_id=empregado.empresa_id,
            empregado=empregado,
        )
        .filter(_filtro_tem_relatorio_tecnico())
        .order_by("-data", "-criado_em")
    )

    projeto_id = (filtros.get("projeto") or "").strip()
    furo_id = (filtros.get("furo") or "").strip()
    data_inicio = (filtros.get("data_inicio") or "").strip()
    data_fim = (filtros.get("data_fim") or "").strip()
    texto = (filtros.get("q") or "").strip()

    if projeto_id:
        queryset = queryset.filter(projeto_id=projeto_id)
    if furo_id:
        queryset = queryset.filter(furo_id=furo_id)
    if data_inicio:
        data_inicio_parsed = parse_date(data_inicio)
        if data_inicio_parsed:
            queryset = queryset.filter(data__gte=data_inicio_parsed)
    if data_fim:
        data_fim_parsed = parse_date(data_fim)
        if data_fim_parsed:
            queryset = queryset.filter(data__lte=data_fim_parsed)
    if texto:
        queryset = queryset.filter(
            Q(projeto__nome__icontains=texto)
            | Q(furo__nome__icontains=texto)
            | Q(numero_relatorio__icontains=texto)
            | Q(cliente__icontains=texto)
        )

    return {
        "relatorios": queryset,
        "filtros": {
            "projeto": projeto_id,
            "furo": furo_id,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "q": texto,
        },
        "totais": {
            "total": queryset.count(),
        },
    }


def obter_relatorios_turno_admin_filtrados(empresa, filtros=None):
    filtros = filtros or {}
    empresa_id = _resolver_empresa_id(empresa)
    queryset = (
        RegistoDiarioEmpregado.objects.select_related(
            "empregado",
            "projeto",
            "furo",
            "planeamento_turno",
            "planeamento_turno__maquina",
        )
        .filter(
            empresa_id=empresa_id,
            empregado__empresa_id=empresa_id,
        )
        .filter(_filtro_tem_relatorio_tecnico())
        .order_by("-data", "-criado_em")
    )

    empregado_id = (filtros.get("empregado") or "").strip()
    projeto_id = (filtros.get("projeto") or "").strip()
    furo_id = (filtros.get("furo") or "").strip()
    data_inicio = (filtros.get("data_inicio") or "").strip()
    data_fim = (filtros.get("data_fim") or "").strip()
    texto = (filtros.get("q") or "").strip()

    if empregado_id:
        queryset = queryset.filter(empregado_id=empregado_id)
    if projeto_id:
        queryset = queryset.filter(projeto_id=projeto_id)
    if furo_id:
        queryset = queryset.filter(furo_id=furo_id)
    if data_inicio:
        data_inicio_parsed = parse_date(data_inicio)
        if data_inicio_parsed:
            queryset = queryset.filter(data__gte=data_inicio_parsed)
    if data_fim:
        data_fim_parsed = parse_date(data_fim)
        if data_fim_parsed:
            queryset = queryset.filter(data__lte=data_fim_parsed)
    if texto:
        queryset = queryset.filter(
            Q(numero_relatorio__icontains=texto)
            | Q(cliente__icontains=texto)
            | Q(projeto__nome__icontains=texto)
            | Q(furo__nome__icontains=texto)
            | Q(empregado__nome__icontains=texto)
        )

    return {
        "relatorios": queryset,
        "filtros": {
            "empregado": empregado_id,
            "projeto": projeto_id,
            "furo": furo_id,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "q": texto,
        },
        "totais": {
            "total": queryset.count(),
        },
    }
