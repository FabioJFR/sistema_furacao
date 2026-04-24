from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from projetos.models import Empregados, Furo, Projeto, RegistoDiarioEmpregado


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def obter_registos_empregado(empregado):
    return (
        empregado.registos_diarios.select_related("projeto", "furo")
        .filter(empresa_id=empregado.empresa_id)
        .order_by("-data", "-criado_em")
    )


def obter_registo_empregado(empregado, pk):
    return get_object_or_404(
        RegistoDiarioEmpregado,
        pk=pk,
        empregado=empregado,
        empresa_id=empregado.empresa_id,
    )


def obter_registos_admin_filtrados(empresa, filtros):
    empresa_id = _resolver_empresa_id(empresa)
    queryset = (
        RegistoDiarioEmpregado.objects.select_related("empregado", "projeto", "furo")
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
        RegistoDiarioEmpregado.objects.select_related("empregado", "projeto", "furo"),
        pk=pk,
        empresa_id=empresa_id,
        empregado__empresa_id=empresa_id,
    )
