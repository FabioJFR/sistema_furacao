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


def obter_intervalo_filtros(request):
    hoje = timezone.now().date()

    periodo = request.GET.get("periodo", "30_dias")
    data_inicio_raw = request.GET.get("data_inicio")
    data_fim_raw = request.GET.get("data_fim")
    projeto_id = request.GET.get("projeto") or None
    empregado_id = request.GET.get("empregado") or None

    def normalizar_data(valor):
        if not valor:
            return None
        if isinstance(valor, date):
            return valor
        if isinstance(valor, str):
            return parse_date(valor)
        return None

    data_inicio = normalizar_data(data_inicio_raw)
    data_fim = normalizar_data(data_fim_raw)

    if periodo == "hoje":
        inicio = hoje
        fim = hoje

    elif periodo == "7_dias":
        inicio = hoje - timedelta(days=7)
        fim = hoje

    elif periodo == "30_dias":
        inicio = hoje - timedelta(days=30)
        fim = hoje

    elif periodo == "mes":
        inicio = hoje.replace(day=1)
        fim = hoje

    elif periodo == "personalizado":
        inicio = data_inicio or (hoje - timedelta(days=30))
        fim = data_fim or hoje

    else:
        inicio = hoje - timedelta(days=30)
        fim = hoje

    return inicio, fim, projeto_id, empregado_id


def aplicar_filtros_registos(queryset, inicio=None, fim=None, projeto_id=None, empregado_id=None):
    if inicio:
        queryset = queryset.filter(data__gte=inicio)
    if fim:
        queryset = queryset.filter(data__lte=fim)
    if projeto_id:
        queryset = queryset.filter(projeto_id=projeto_id)
    if empregado_id:
        queryset = queryset.filter(empregado_id=empregado_id)
    return queryset


def obter_opcoes_filtros_dashboard():
    return {
        "projetos_filtro": Projeto.objects.all().order_by("nome"),
        "empregados_filtro": Empregados.objects.all().order_by("nome"),
    }


def obter_cards_dashboard(inicio=None, fim=None, projeto_id=None, empregado_id=None):
    registos = aplicar_filtros_registos(
        RegistoDiarioEmpregado.objects.all(),
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
    )

    total_metros = registos.aggregate(total=Sum("metros_furados"))["total"] or 0
    total_horas = registos.aggregate(total=Sum("horas_trabalhadas"))["total"] or 0
    total_registos = registos.count()

    produtividade_media = round(float(total_metros) / float(total_horas), 2) if total_horas else 0

    empregados_ativos = registos.values("empregado_id").distinct().count()
    furos_ativos = registos.exclude(furo__isnull=True).values("furo_id").distinct().count()
    projetos_ativos = registos.exclude(projeto__isnull=True).values("projeto_id").distinct().count()

    return {
        "total_projetos": Projeto.objects.count(),
        "total_furos": Furo.objects.count(),
        "total_empregados": Empregados.objects.count(),
        "total_maquinas": Maquina.objects.count(),
        "total_materiais": Material.objects.count(),
        "total_metros": round(float(total_metros), 2),
        "total_horas": round(float(total_horas), 2),
        "total_registos": total_registos,
        "produtividade_media": produtividade_media,
        "empregados_ativos": empregados_ativos,
        "furos_ativos": furos_ativos,
        "projetos_ativos": projetos_ativos,
    }


def obter_alertas_dashboard(inicio=None, fim=None, projeto_id=None, empregado_id=None):
    materiais_stock_baixo = Material.objects.filter(
        ativo=True,
        quantidade__lte=F("stock_minimo"),
    ).order_by("quantidade")

    maquinas_alerta = Maquina.objects.filter(
        estado__in=["avariada", "reparacao", "parada"],
    ).order_by("nome")

    registos = aplicar_filtros_registos(
        RegistoDiarioEmpregado.objects.all(),
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
    )

    furos_baixa_producao = (
        registos.exclude(furo__isnull=True)
        .values("furo__id", "furo__nome")
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


def obter_graficos_dashboard(inicio=None, fim=None, projeto_id=None, empregado_id=None, request=None):
    hoje = timezone.now().date()

    if fim is None:
        fim = hoje

    if inicio is None:
        inicio = fim - timedelta(days=30)

    registos = aplicar_filtros_registos(
        RegistoDiarioEmpregado.objects.all(),
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
    )

    # PRODUÇÃO POR DIA
    registos_por_dia = (
        registos.values("data")
        .annotate(
            metros=Sum("metros_furados"),
            horas=Sum("horas_trabalhadas"),
        )
        .order_by("data")
    )

    labels_dia = [r["data"].strftime("%d/%m/%Y") for r in registos_por_dia]
    metros_dia = [float(r["metros"] or 0) for r in registos_por_dia]
    horas_dia = [float(r["horas"] or 0) for r in registos_por_dia]
    produtividade_dia = [
        round((float(r["metros"] or 0) / float(r["horas"] or 0)), 2) if (r["horas"] or 0) else 0
        for r in registos_por_dia
    ]

    # PRODUÇÃO POR EMPREGADO
    top_empregados = (
        registos.values("empregado__nome")
        .annotate(
            total_metros=Sum("metros_furados"),
            total_horas=Sum("horas_trabalhadas"),
        )
        .order_by("-total_metros")[:10]
    )

    labels_empregados = [r["empregado__nome"] or "-" for r in top_empregados]
    metros_empregados = [float(r["total_metros"] or 0) for r in top_empregados]
    horas_empregados = [float(r["total_horas"] or 0) for r in top_empregados]

    # PRODUÇÃO POR FURO
    top_furos = (
        registos.values("furo__nome")
        .annotate(
            total_metros=Sum("metros_furados"),
            total_horas=Sum("horas_trabalhadas"),
        )
        .order_by("-total_metros")[:10]
    )

    labels_furos = [r["furo__nome"] or "-" for r in top_furos]
    metros_furos = [float(r["total_metros"] or 0) for r in top_furos]
    horas_furos = [float(r["total_horas"] or 0) for r in top_furos]

    # PRODUÇÃO POR PROJETO
    top_projetos = (
        registos.values("projeto__nome")
        .annotate(
            total_metros=Sum("metros_furados"),
            total_horas=Sum("horas_trabalhadas"),
        )
        .order_by("-total_metros")[:10]
    )

    labels_projetos = [r["projeto__nome"] or "-" for r in top_projetos]
    metros_projetos = [float(r["total_metros"] or 0) for r in top_projetos]

    # Compatibilidade com templates antigos
    labels = labels_dia
    dados_metros = metros_dia
    dados_horas = horas_dia
    dados_produtividade = produtividade_dia

    return {
        "labels_dia": labels_dia,
        "metros_dia": metros_dia,
        "horas_dia": horas_dia,
        "produtividade_dia": produtividade_dia,
        "labels_empregados": labels_empregados,
        "metros_empregados": metros_empregados,
        "horas_empregados": horas_empregados,
        "labels_furos": labels_furos,
        "metros_furos": metros_furos,
        "horas_furos": horas_furos,
        "labels_projetos": labels_projetos,
        "metros_projetos": metros_projetos,
        "labels": labels,
        "dados_metros": dados_metros,
        "dados_horas": dados_horas,
        "dados_produtividade": dados_produtividade,
    }