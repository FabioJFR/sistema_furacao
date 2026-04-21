from datetime import date, timedelta

from django.db.models import F, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from projetos.models import (
    Empregados,
    Furo,
    Maquina,
    Material,
    Projeto,
    RegistoDiarioEmpregado,
)



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _filtrar_por_empresa(queryset, empresa=None, campo="empresa_id"):
    if empresa is None:
        return queryset

    empresa_id = _resolver_empresa_id(empresa)
    return queryset.filter(**{campo: empresa_id})



def _normalizar_data(valor):
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        return parse_date(valor)
    return None



def _obter_queryset_base_registos():
    return RegistoDiarioEmpregado.objects.all()



def _obter_opcoes_periodo(hoje, periodo, data_inicio=None, data_fim=None):
    if periodo == "hoje":
        return hoje, hoje

    if periodo == "7_dias":
        return hoje - timedelta(days=7), hoje

    if periodo == "30_dias":
        return hoje - timedelta(days=30), hoje

    if periodo == "mes":
        return hoje.replace(day=1), hoje

    if periodo == "personalizado":
        return data_inicio or (hoje - timedelta(days=30)), data_fim or hoje

    return hoje - timedelta(days=30), hoje



def _validar_filtro_projeto(projeto_id, empresa=None):
    if empresa is None or not projeto_id:
        return projeto_id

    empresa_id = _resolver_empresa_id(empresa)
    existe = Projeto.objects.filter(pk=projeto_id, empresa_id=empresa_id).exists()
    return projeto_id if existe else None



def _validar_filtro_empregado(empregado_id, empresa=None):
    if empresa is None or not empregado_id:
        return empregado_id

    empresa_id = _resolver_empresa_id(empresa)
    existe = Empregados.objects.filter(pk=empregado_id, empresa_id=empresa_id).exists()
    return empregado_id if existe else None



def _obter_series_por_dia(registos_por_dia):
    labels_dia = [r["data"].strftime("%d/%m/%Y") for r in registos_por_dia]
    metros_dia = [float(r["metros"] or 0) for r in registos_por_dia]
    horas_dia = [float(r["horas"] or 0) for r in registos_por_dia]
    produtividade_dia = [
        round((float(r["metros"] or 0) / float(r["horas"] or 0)), 2)
        if (r["horas"] or 0)
        else 0
        for r in registos_por_dia
    ]

    return {
        "labels_dia": labels_dia,
        "metros_dia": metros_dia,
        "horas_dia": horas_dia,
        "produtividade_dia": produtividade_dia,
    }



def _obter_top_series(queryset, campo_nome, limite=10):
    top_items = (
        queryset.values(campo_nome)
        .annotate(
            total_metros=Sum("metros_furados"),
            total_horas=Sum("horas_trabalhadas"),
        )
        .order_by("-total_metros")[:limite]
    )

    labels = [r[campo_nome] or "-" for r in top_items]
    metros = [float(r["total_metros"] or 0) for r in top_items]
    horas = [float(r["total_horas"] or 0) for r in top_items]

    return labels, metros, horas



def obter_intervalo_filtros(request, empresa=None):
    hoje = timezone.now().date()

    periodo = request.GET.get("periodo", "30_dias")
    data_inicio_raw = request.GET.get("data_inicio")
    data_fim_raw = request.GET.get("data_fim")
    projeto_id = request.GET.get("projeto") or None
    empregado_id = request.GET.get("empregado") or None

    data_inicio = _normalizar_data(data_inicio_raw)
    data_fim = _normalizar_data(data_fim_raw)
    inicio, fim = _obter_opcoes_periodo(hoje, periodo, data_inicio, data_fim)

    projeto_id = _validar_filtro_projeto(projeto_id, empresa)
    empregado_id = _validar_filtro_empregado(empregado_id, empresa)

    return inicio, fim, projeto_id, empregado_id



def aplicar_filtros_registos(
    queryset,
    inicio=None,
    fim=None,
    projeto_id=None,
    empregado_id=None,
    empresa=None,
):
    queryset = _filtrar_por_empresa(queryset, empresa)

    if inicio:
        queryset = queryset.filter(data__gte=inicio)
    if fim:
        queryset = queryset.filter(data__lte=fim)
    if projeto_id:
        queryset = queryset.filter(projeto_id=projeto_id)
    if empregado_id:
        queryset = queryset.filter(empregado_id=empregado_id)

    return queryset



def obter_opcoes_filtros_dashboard(empresa=None):
    projetos_qs = _filtrar_por_empresa(Projeto.objects.all().order_by("nome"), empresa)
    empregados_qs = _filtrar_por_empresa(Empregados.objects.all().order_by("nome"), empresa)

    return {
        "projetos_filtro": projetos_qs,
        "empregados_filtro": empregados_qs,
    }



def obter_cards_dashboard(inicio=None, fim=None, projeto_id=None, empregado_id=None, empresa=None):
    registos = aplicar_filtros_registos(
        _obter_queryset_base_registos(),
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
        empresa=empresa,
    )

    agregados = registos.aggregate(
        total_metros=Sum("metros_furados"),
        total_horas=Sum("horas_trabalhadas"),
    )
    total_metros = agregados["total_metros"] or 0
    total_horas = agregados["total_horas"] or 0
    total_registos = registos.count()

    produtividade_media = round(float(total_metros) / float(total_horas), 2) if total_horas else 0

    empregados_ativos_qs = registos
    furos_ativos_qs = registos.exclude(furo__isnull=True)
    projetos_ativos_qs = registos.exclude(projeto__isnull=True)

    if empresa is not None:
        empresa_id = _resolver_empresa_id(empresa)
        empregados_ativos_qs = empregados_ativos_qs.filter(empregado__empresa_id=empresa_id)
        furos_ativos_qs = furos_ativos_qs.filter(furo__empresa_id=empresa_id)
        projetos_ativos_qs = projetos_ativos_qs.filter(projeto__empresa_id=empresa_id)

    projetos_qs = _filtrar_por_empresa(Projeto.objects.all(), empresa)
    furos_qs = _filtrar_por_empresa(Furo.objects.all(), empresa)
    empregados_qs = _filtrar_por_empresa(Empregados.objects.all(), empresa)
    maquinas_qs = _filtrar_por_empresa(Maquina.objects.all(), empresa)
    materiais_qs = _filtrar_por_empresa(Material.objects.all(), empresa)

    return {
        "total_projetos": projetos_qs.count(),
        "total_furos": furos_qs.count(),
        "total_empregados": empregados_qs.count(),
        "total_empregados_pendentes": empregados_qs.filter(aprovado=False).count(),
        "total_maquinas": maquinas_qs.count(),
        "total_materiais": materiais_qs.count(),
        "total_metros": round(float(total_metros), 2),
        "total_horas": round(float(total_horas), 2),
        "total_registos": total_registos,
        "produtividade_media": produtividade_media,
        "empregados_ativos": empregados_ativos_qs.values("empregado_id").distinct().count(),
        "furos_ativos": furos_ativos_qs.values("furo_id").distinct().count(),
        "projetos_ativos": projetos_ativos_qs.values("projeto_id").distinct().count(),
    }



def obter_alertas_dashboard(inicio=None, fim=None, projeto_id=None, empregado_id=None, empresa=None):
    materiais_stock_baixo = Material.objects.filter(
        ativo=True,
        quantidade__lte=F("stock_minimo"),
    ).order_by("quantidade")

    maquinas_alerta = Maquina.objects.filter(
        estado__in=["avariada", "reparacao", "parada"],
    ).order_by("nome")

    materiais_stock_baixo = _filtrar_por_empresa(materiais_stock_baixo, empresa)
    maquinas_alerta = _filtrar_por_empresa(maquinas_alerta, empresa)

    registos = aplicar_filtros_registos(
        _obter_queryset_base_registos(),
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
        empresa=empresa,
    )

    furos_baixa_producao_qs = registos.exclude(furo__isnull=True)

    if empresa is not None:
        empresa_id = _resolver_empresa_id(empresa)
        furos_baixa_producao_qs = furos_baixa_producao_qs.filter(furo__empresa_id=empresa_id)

    furos_baixa_producao = (
        furos_baixa_producao_qs.values("furo__id", "furo__nome")
        .annotate(
            total_metros=Sum("metros_furados"),
            total_horas=Sum("horas_trabalhadas"),
        )
        .order_by("total_metros")[:5]
    )

    return {
        "materiais_stock_baixo": materiais_stock_baixo,
        "maquinas_alerta": maquinas_alerta,
        "furos_baixa_producao": furos_baixa_producao,
    }



def obter_graficos_dashboard(inicio=None, fim=None, projeto_id=None, empregado_id=None, empresa=None, request=None):
    hoje = timezone.now().date()

    if fim is None:
        fim = hoje
    if inicio is None:
        inicio = fim - timedelta(days=30)

    registos = aplicar_filtros_registos(
        _obter_queryset_base_registos(),
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
        empresa=empresa,
    )

    registos_empregados = registos
    registos_furos = registos.exclude(furo__isnull=True)
    registos_projetos = registos.exclude(projeto__isnull=True)

    if empresa is not None:
        empresa_id = _resolver_empresa_id(empresa)
        registos_empregados = registos_empregados.filter(empregado__empresa_id=empresa_id)
        registos_furos = registos_furos.filter(furo__empresa_id=empresa_id)
        registos_projetos = registos_projetos.filter(projeto__empresa_id=empresa_id)

    registos_por_dia = (
        registos.values("data")
        .annotate(
            metros=Sum("metros_furados"),
            horas=Sum("horas_trabalhadas"),
        )
        .order_by("data")
    )

    series_dia = _obter_series_por_dia(registos_por_dia)
    labels_empregados, metros_empregados, horas_empregados = _obter_top_series(
        registos_empregados,
        "empregado__nome",
    )
    labels_furos, metros_furos, horas_furos = _obter_top_series(
        registos_furos,
        "furo__nome",
    )
    labels_projetos, metros_projetos, _ = _obter_top_series(
        registos_projetos,
        "projeto__nome",
    )

    return {
        **series_dia,
        "labels_empregados": labels_empregados,
        "metros_empregados": metros_empregados,
        "horas_empregados": horas_empregados,
        "labels_furos": labels_furos,
        "metros_furos": metros_furos,
        "horas_furos": horas_furos,
        "labels_projetos": labels_projetos,
        "metros_projetos": metros_projetos,
        "labels": series_dia["labels_dia"],
        "dados_metros": series_dia["metros_dia"],
        "dados_horas": series_dia["horas_dia"],
        "dados_produtividade": series_dia["produtividade_dia"],
    }
