from collections import OrderedDict
from datetime import timedelta

from django.db.models import Sum, F, Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import (
    Projeto,
    Furo,
    Empregados,
    Maquina,
    Material,
    RegistoDiarioEmpregado,
)


def obter_intervalo_filtros(request):
    hoje = timezone.now().date()

    periodo = request.GET.get("periodo", "30_dias")
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")
    projeto_id = request.GET.get("projeto")
    empregado_id = request.GET.get("empregado")

    inicio = None
    fim = hoje

    if periodo == "hoje":
        inicio = hoje
    elif periodo == "7_dias":
        inicio = hoje - timedelta(days=6)
    elif periodo == "30_dias":
        inicio = hoje - timedelta(days=29)
    elif periodo == "mes":
        inicio = hoje.replace(day=1)
    elif periodo == "personalizado":
        inicio = parse_date(data_inicio) if data_inicio else None
        fim = parse_date(data_fim) if data_fim else hoje

    return {
        "periodo": periodo,
        "inicio": inicio,
        "fim": fim,
        "data_inicio": data_inicio or "",
        "data_fim": data_fim or "",
        "projeto_id": projeto_id or "",
        "empregado_id": empregado_id or "",
    }


def obter_cards_dashboard():
    return {
        "total_projetos": Projeto.objects.count(),
        "total_furos": Furo.objects.count(),
        "total_empregados": Empregados.objects.count(),
        "total_maquinas": Maquina.objects.count(),
        "total_materiais": Material.objects.count(),
    }


def obter_alertas_dashboard():
    materiais_stock_baixo = Material.objects.filter(
        ativo=True,
        quantidade__lte=F("stock_minimo")
    ).order_by("quantidade")

    maquinas_alerta = Maquina.objects.filter(
        estado__in=["avariada", "reparacao", "parada"]
    ).order_by("nome")

    return {
        "materiais_stock_baixo": materiais_stock_baixo,
        "maquinas_alerta": maquinas_alerta,
    }


def obter_opcoes_filtros_dashboard():
    return {
        "projetos_filtro": Projeto.objects.all().order_by("nome"),
        "empregados_filtro": Empregados.objects.all().order_by("nome"),
    }


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

from collections import OrderedDict
from django.db.models import Sum, Q


def obter_graficos_dashboard(inicio=None, fim=None, projeto_id=None, empregado_id=None):
    registos = RegistoDiarioEmpregado.objects.select_related(
        "empregado", "projeto", "furo"
    ).order_by("data")

    registos = aplicar_filtros_registos(
        registos,
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
    )

    # -------- AGREGADO POR DIA --------
    agregados_dia = OrderedDict()

    for registo in registos:
        if not registo.data:
            continue

        chave = registo.data.strftime("%d/%m/%Y")

        if chave not in agregados_dia:
            agregados_dia[chave] = {
                "metros": 0,
                "horas": 0,
            }

        agregados_dia[chave]["metros"] += registo.metros_furados or 0
        agregados_dia[chave]["horas"] += registo.horas_trabalhadas or 0

    labels_dia = []
    metros_dia = []
    horas_dia = []
    produtividade_dia = []

    for data_label, valores in agregados_dia.items():
        labels_dia.append(data_label)

        metros = valores["metros"]
        horas = valores["horas"]
        produtividade = metros / horas if horas > 0 else 0

        metros_dia.append(round(metros, 2))
        horas_dia.append(round(horas, 2))
        produtividade_dia.append(round(produtividade, 2))

    # -------- FILTROS DINÂMICOS PARA ANNOTATE --------
    filtro_empregados = Q()
    filtro_projetos = Q()
    filtro_furos = Q()

    if inicio:
        filtro_empregados &= Q(registos_diarios__data__gte=inicio)
        filtro_projetos &= Q(registos_empregados__data__gte=inicio)
        filtro_furos &= Q(registos_empregados__data__gte=inicio)

    if fim:
        filtro_empregados &= Q(registos_diarios__data__lte=fim)
        filtro_projetos &= Q(registos_empregados__data__lte=fim)
        filtro_furos &= Q(registos_empregados__data__lte=fim)

    if projeto_id:
        filtro_empregados &= Q(registos_diarios__projeto_id=projeto_id)
        filtro_furos &= Q(registos_empregados__projeto_id=projeto_id)

    if empregado_id:
        filtro_projetos &= Q(registos_empregados__empregado_id=empregado_id)
        filtro_furos &= Q(registos_empregados__empregado_id=empregado_id)

    # -------- TOP EMPREGADOS --------
    empregados_stats = (
        Empregados.objects.annotate(
            total_metros=Sum("registos_diarios__metros_furados", filter=filtro_empregados)
        )
        .filter(total_metros__gt=0)
        .order_by("-total_metros")[:10]
    )

    labels_empregados = [e.nome for e in empregados_stats]
    metros_empregados = [round(e.total_metros or 0, 2) for e in empregados_stats]

    # -------- TOP PROJETOS --------
    projetos_stats = (
        Projeto.objects.annotate(
            total_metros=Sum("registos_empregados__metros_furados", filter=filtro_projetos)
        )
        .filter(total_metros__gt=0)
        .order_by("-total_metros")[:10]
    )

    labels_projetos = [p.nome for p in projetos_stats]
    metros_projetos = [round(p.total_metros or 0, 2) for p in projetos_stats]

    # -------- TOP FUROS --------
    furos_stats = (
        Furo.objects.annotate(
            total_metros=Sum("registos_empregados__metros_furados", filter=filtro_furos)
        )
        .filter(total_metros__gt=0)
        .order_by("-total_metros")[:10]
    )

    labels_furos = [f.nome for f in furos_stats]
    metros_furos = [round(f.total_metros or 0, 2) for f in furos_stats]

    return {
        "labels_dia": labels_dia,
        "metros_dia": metros_dia,
        "horas_dia": horas_dia,
        "produtividade_dia": produtividade_dia,
        "labels_empregados": labels_empregados,
        "metros_empregados": metros_empregados,
        "labels_projetos": labels_projetos,
        "metros_projetos": metros_projetos,
        "labels_furos": labels_furos,
        "metros_furos": metros_furos,
    }
    registos = RegistoDiarioEmpregado.objects.select_related(
        "empregado", "projeto", "furo"
    ).order_by("data")

    registos = aplicar_filtros_registos(
        registos,
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
    )

    agregados_dia = OrderedDict()

    for registo in registos:
        if not registo.data:
            continue

        chave = registo.data.strftime("%d/%m/%Y")

        if chave not in agregados_dia:
            agregados_dia[chave] = {
                "metros": 0,
                "horas": 0,
            }

        agregados_dia[chave]["metros"] += registo.metros_furados or 0
        agregados_dia[chave]["horas"] += registo.horas_trabalhadas or 0

    labels_dia = []
    metros_dia = []
    horas_dia = []
    produtividade_dia = []

    for data_label, valores in agregados_dia.items():
        labels_dia.append(data_label)

        metros = valores["metros"]
        horas = valores["horas"]
        produtividade = metros / horas if horas > 0 else 0

        metros_dia.append(round(metros, 2))
        horas_dia.append(round(horas, 2))
        produtividade_dia.append(round(produtividade, 2))

    # -------- TOP EMPREGADOS FILTRADO --------
    empregados_labels = []
    empregados_metros = []

    for empregado in Empregados.objects.all():
        regs = empregado.registos_diarios.all()
        regs = aplicar_filtros_registos(
            regs,
            inicio=inicio,
            fim=fim,
            projeto_id=projeto_id,
        )

        total = regs.aggregate(total=Sum("metros_furados"))["total"] or 0

        if total > 0:
            empregados_labels.append(empregado.nome)
            empregados_metros.append(round(total, 2))

    top_empregados = sorted(
        zip(empregados_labels, empregados_metros),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    labels_empregados = [x[0] for x in top_empregados]
    metros_empregados = [x[1] for x in top_empregados]

    # -------- TOP PROJETOS FILTRADO --------
    projetos_labels = []
    projetos_metros = []

    for projeto in Projeto.objects.all():
        regs = projeto.registos_empregados.all()
        regs = aplicar_filtros_registos(
            regs,
            inicio=inicio,
            fim=fim,
            empregado_id=empregado_id,
        )

        total = regs.aggregate(total=Sum("metros_furados"))["total"] or 0

        if total > 0:
            projetos_labels.append(projeto.nome)
            projetos_metros.append(round(total, 2))

    top_projetos = sorted(
        zip(projetos_labels, projetos_metros),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    labels_projetos = [x[0] for x in top_projetos]
    metros_projetos = [x[1] for x in top_projetos]

    # -------- TOP FUROS FILTRADO --------
    furos_labels = []
    furos_metros = []

    for furo in Furo.objects.all():
        regs = furo.registos_empregados.all()
        regs = aplicar_filtros_registos(
            regs,
            inicio=inicio,
            fim=fim,
            projeto_id=projeto_id,
            empregado_id=empregado_id,
        )

        total = regs.aggregate(total=Sum("metros_furados"))["total"] or 0

        if total > 0:
            furos_labels.append(furo.nome)
            furos_metros.append(round(total, 2))

    top_furos = sorted(
        zip(furos_labels, furos_metros),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    labels_furos = [x[0] for x in top_furos]
    metros_furos = [x[1] for x in top_furos]

    return {
        "labels_dia": labels_dia,
        "metros_dia": metros_dia,
        "horas_dia": horas_dia,
        "produtividade_dia": produtividade_dia,
        "labels_empregados": labels_empregados,
        "metros_empregados": metros_empregados,
        "labels_projetos": labels_projetos,
        "metros_projetos": metros_projetos,
        "labels_furos": labels_furos,
        "metros_furos": metros_furos,
    }