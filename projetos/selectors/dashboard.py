from datetime import date, timedelta

from django.db.models import F, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from plataforma.models import Empresa
from projetos.models import (
    DevolucaoMaterial,
    Despesa,
    Empregados,
    Furo,
    LevantamentoMaterial,
    Maquina,
    MaquinaAvaria,
    Material,
    Projeto,
    RegistoDiarioEmpregado,
    SalarioBaseFuncao,
)


def obter_empresas_contexto_dashboard():
    return Empresa.objects.select_related("plano").all().order_by("nome")


def resolver_empresa_contexto_global_dashboard(empresa_id=None):
    empresas_qs = obter_empresas_contexto_dashboard()
    if empresa_id:
        empresa = empresas_qs.filter(pk=empresa_id).first()
        if empresa:
            return empresa, "querystring"
    return empresas_qs.first(), "fallback_primeira"


def obter_empresa_dashboard_por_id(empresa_id):
    if not empresa_id:
        return None
    return Empresa.objects.select_related("plano").filter(pk=empresa_id).first()


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


def _obter_queryset_base_despesas():
    return Despesa.objects.all()



def _obter_opcoes_periodo(hoje, periodo, data_inicio=None, data_fim=None):
    if periodo == "total":
        return None, None

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


def _mapa_custo_materiais_empresa(empresa=None, projeto_id=None):
    materiais_qs = _filtrar_por_empresa(Material.objects.all(), empresa)
    if projeto_id:
        materiais_qs = materiais_qs.filter(projeto_id=projeto_id)

    material_info = {
        material_id: {
            "valor": float(valor or 0),
            "projeto_id": projeto_ref,
            "furo_id": furo_ref,
        }
        for material_id, valor, projeto_ref, furo_ref in materiais_qs.values_list("id", "valor", "projeto_id", "furo_id")
    }

    consumos = {}
    levantamentos = _filtrar_por_empresa(LevantamentoMaterial.objects.all(), empresa)
    devolucoes = _filtrar_por_empresa(DevolucaoMaterial.objects.all(), empresa)
    if projeto_id:
        levantamentos = levantamentos.filter(projeto_id=projeto_id)
        devolucoes = devolucoes.filter(projeto_id=projeto_id)

    for material_id, quantidade, projeto_ref, furo_ref in levantamentos.values_list(
        "material_id", "quantidade", "projeto_id", "furo_id"
    ):
        if material_id not in material_info:
            continue
        key = str(material_id)
        entry = consumos.setdefault(
            key,
            {
                "quantidade": 0.0,
                "projeto_id": projeto_ref or material_info[material_id]["projeto_id"],
                "furo_id": furo_ref or material_info[material_id]["furo_id"],
                "valor": material_info[material_id]["valor"],
            },
        )
        entry["quantidade"] += float(quantidade or 0)

    for material_id, quantidade, projeto_ref, furo_ref in devolucoes.values_list(
        "material_id", "quantidade", "projeto_id", "furo_id"
    ):
        if material_id not in material_info:
            continue
        key = str(material_id)
        entry = consumos.setdefault(
            key,
            {
                "quantidade": 0.0,
                "projeto_id": projeto_ref or material_info[material_id]["projeto_id"],
                "furo_id": furo_ref or material_info[material_id]["furo_id"],
                "valor": material_info[material_id]["valor"],
            },
        )
        entry["quantidade"] -= float(quantidade or 0)

    return consumos


def _obter_resumos_financeiros(empresa=None, projeto_id=None, custo_por_metro_cliente=0):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    furos_qs = _filtrar_por_empresa(Furo.objects.all(), empresa)
    projetos_qs = _filtrar_por_empresa(Projeto.objects.all(), empresa)
    despesas_qs = _filtrar_por_empresa(Despesa.objects.all(), empresa)

    if projeto_id:
        furos_qs = furos_qs.filter(projeto_id=projeto_id)
        projetos_qs = projetos_qs.filter(pk=projeto_id)
        despesas_qs = despesas_qs.filter(projeto_id=projeto_id)

    metros_por_projeto = {
        item["projeto_id"]: float(item["total"] or 0)
        for item in furos_qs.values("projeto_id").annotate(total=Sum("metros_furados"))
    }
    metros_por_furo = {
        item["id"]: float(item["metros_furados"] or 0)
        for item in furos_qs.values("id", "metros_furados")
    }

    gastos_despesa_projeto = {}
    gastos_despesa_furo = {}
    gastos_despesa_maquina_projeto = {}
    gastos_despesa_maquina_furo = {}

    for item in despesas_qs.values("projeto_id").annotate(total=Sum("valor")):
        gastos_despesa_projeto[item["projeto_id"]] = float(item["total"] or 0)
    for item in despesas_qs.values("furo_id").annotate(total=Sum("valor")):
        gastos_despesa_furo[item["furo_id"]] = float(item["total"] or 0)
    for item in despesas_qs.exclude(maquina__isnull=True).values("projeto_id").annotate(total=Sum("valor")):
        gastos_despesa_maquina_projeto[item["projeto_id"]] = float(item["total"] or 0)
    for item in despesas_qs.exclude(maquina__isnull=True).values("furo_id").annotate(total=Sum("valor")):
        gastos_despesa_maquina_furo[item["furo_id"]] = float(item["total"] or 0)

    consumos = _mapa_custo_materiais_empresa(empresa=empresa, projeto_id=projeto_id)
    gastos_materiais_projeto = {}
    gastos_materiais_furo = {}
    for item in consumos.values():
        custo = max(float(item["quantidade"] or 0), 0) * float(item["valor"] or 0)
        projeto_ref = item["projeto_id"]
        furo_ref = item["furo_id"]
        gastos_materiais_projeto[projeto_ref] = gastos_materiais_projeto.get(projeto_ref, 0.0) + custo
        if furo_ref:
            gastos_materiais_furo[furo_ref] = gastos_materiais_furo.get(furo_ref, 0.0) + custo

    resumos_projeto = []
    for projeto in projetos_qs.order_by("nome"):
        metros = round(metros_por_projeto.get(projeto.pk, 0.0), 2)
        gasto = round(gastos_despesa_projeto.get(projeto.pk, 0.0) + gastos_materiais_projeto.get(projeto.pk, 0.0), 2)
        ganho = round(metros * float(custo_por_metro_cliente or 0), 2)
        margem_total = round(ganho - gasto, 2)
        margem_metro = round(margem_total / metros, 2) if metros else 0.0
        custo_metro = round(gasto / metros, 2) if metros else 0.0
        margem_percentual = round((margem_total / ganho) * 100, 2) if ganho else 0.0
        resumos_projeto.append(
            {
                "id": projeto.pk,
                "nome": projeto.nome,
                "metros": metros,
                "gasto": gasto,
                "ganho": ganho,
                "margem_total": margem_total,
                "margem_metro": margem_metro,
                "margem_percentual": margem_percentual,
                "custo_metro": custo_metro,
                "gasto_maquinas": round(gastos_despesa_maquina_projeto.get(projeto.pk, 0.0), 2),
                "gasto_materiais": round(gastos_materiais_projeto.get(projeto.pk, 0.0), 2),
            }
        )

    resumos_furo = []
    furos = furos_qs.select_related("projeto").order_by("projeto__nome", "nome")
    for furo in furos:
        metros = round(metros_por_furo.get(furo.pk, 0.0), 2)
        gasto = round(gastos_despesa_furo.get(furo.pk, 0.0) + gastos_materiais_furo.get(furo.pk, 0.0), 2)
        ganho = round(metros * float(custo_por_metro_cliente or 0), 2)
        margem_total = round(ganho - gasto, 2)
        margem_metro = round(margem_total / metros, 2) if metros else 0.0
        custo_metro = round(gasto / metros, 2) if metros else 0.0
        margem_percentual = round((margem_total / ganho) * 100, 2) if ganho else 0.0
        resumos_furo.append(
            {
                "id": furo.pk,
                "nome": furo.nome,
                "projeto_nome": furo.projeto.nome if furo.projeto_id else "-",
                "metros": metros,
                "gasto": gasto,
                "ganho": ganho,
                "margem_total": margem_total,
                "margem_metro": margem_metro,
                "margem_percentual": margem_percentual,
                "custo_metro": custo_metro,
                "gasto_maquinas": round(gastos_despesa_maquina_furo.get(furo.pk, 0.0), 2),
                "gasto_materiais": round(gastos_materiais_furo.get(furo.pk, 0.0), 2),
            }
        )

    return resumos_projeto, resumos_furo



def obter_intervalo_filtros(request, empresa=None):
    hoje = timezone.now().date()

    periodo = request.GET.get("periodo", "total")
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


def aplicar_filtros_despesas(queryset, inicio=None, fim=None, projeto_id=None, empresa=None):
    queryset = _filtrar_por_empresa(queryset, empresa)

    if inicio:
        queryset = queryset.filter(data__gte=inicio)
    if fim:
        queryset = queryset.filter(data__lte=fim)
    if projeto_id:
        queryset = queryset.filter(projeto_id=projeto_id)

    return queryset



def obter_opcoes_filtros_dashboard(empresa=None):
    projetos_qs = _filtrar_por_empresa(Projeto.objects.all().order_by("nome"), empresa)
    empregados_qs = _filtrar_por_empresa(Empregados.objects.all().order_by("nome"), empresa)

    return {
        "projetos_filtro": projetos_qs,
        "empregados_filtro": empregados_qs,
    }



def obter_cards_dashboard(inicio=None, fim=None, projeto_id=None, empregado_id=None, empresa=None):
    empresa_obj = empresa if hasattr(empresa, "recalcular_indicadores_financeiros") else None
    if empresa is not None and empresa_obj is None:
        empresa_obj = Projeto.objects.filter(empresa_id=_resolver_empresa_id(empresa)).select_related("empresa").first()
        empresa_obj = getattr(empresa_obj, "empresa", None)
    if empresa_obj is not None:
        empresa_obj.recalcular_indicadores_financeiros()

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
    despesas = aplicar_filtros_despesas(
        _obter_queryset_base_despesas(),
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empresa=empresa,
    )
    total_despesas = float(despesas.aggregate(total=Sum("valor"))["total"] or 0)
    total_dias_periodo = max(((fim or timezone.now().date()) - (inicio or timezone.now().date())).days + 1, 1)
    media_despesa_diaria = round(total_despesas / total_dias_periodo, 2)

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
    avarias_abertas_qs = _filtrar_por_empresa(
        MaquinaAvaria.objects.filter(status__in=["aberta", "em_reparacao"]),
        empresa,
    )

    return {
        "total_projetos": projetos_qs.count(),
        "total_furos": furos_qs.count(),
        "total_empregados": empregados_qs.count(),
        "total_empregados_pendentes": empregados_qs.filter(aprovado=False).count(),
        "total_avarias_maquinas_abertas": avarias_abertas_qs.count(),
        "total_maquinas": maquinas_qs.count(),
        "total_materiais": materiais_qs.count(),
        "total_metros": round(float(total_metros), 2),
        "total_horas": round(float(total_horas), 2),
        "total_despesas": round(total_despesas, 2),
        "media_despesa_diaria": media_despesa_diaria,
        "custo_por_metro_cliente": round(float(getattr(empresa_obj, "custo_por_metro_cliente", 0) or 0), 2),
        "custo_por_metro_empresa": round(float(getattr(empresa_obj, "custo_por_metro_empresa", 0) or 0), 2),
        "valor_total_cobrado_cliente": round(float(getattr(empresa_obj, "valor_total_cobrado_cliente", 0) or 0), 2),
        "valor_total_gasto_projeto": round(float(getattr(empresa_obj, "valor_total_gasto_projeto", 0) or 0), 2),
        "valor_total_gasto_furo": round(float(getattr(empresa_obj, "valor_total_gasto_furo", 0) or 0), 2),
        "valor_total_ganho_furo": round(float(getattr(empresa_obj, "valor_total_ganho_furo", 0) or 0), 2),
        "valor_total_gasto_materias": round(float(getattr(empresa_obj, "valor_total_gasto_materias", 0) or 0), 2),
        "valor_total_gasto_maquinas": round(float(getattr(empresa_obj, "valor_total_gasto_maquinas", 0) or 0), 2),
        "outros_valores_gastos_associados": round(float(getattr(empresa_obj, "outros_valores_gastos_associados", 0) or 0), 2),
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
    periodo = (request.GET.get("periodo") if request else None) or "30_dias"

    # No modo "total", não aplicamos limite temporal.
    if periodo != "total":
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
    despesas = aplicar_filtros_despesas(
        _obter_queryset_base_despesas(),
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
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
    despesas_por_dia = (
        despesas.values("data")
        .annotate(total=Sum("valor"))
        .order_by("data")
    )
    labels_despesas_dia = [r["data"].strftime("%d/%m/%Y") for r in despesas_por_dia]
    valores_despesas_dia = [round(float(r["total"] or 0), 2) for r in despesas_por_dia]

    despesas_por_categoria = (
        despesas.values("categoria")
        .annotate(total=Sum("valor"))
        .order_by("-total")
    )
    labels_despesas_categoria = [r["categoria"] or "sem categoria" for r in despesas_por_categoria]
    valores_despesas_categoria = [round(float(r["total"] or 0), 2) for r in despesas_por_categoria]

    despesas_por_projeto = (
        despesas.exclude(projeto__isnull=True)
        .values("projeto__nome")
        .annotate(total=Sum("valor"))
        .order_by("-total")[:10]
    )
    labels_despesas_projeto = [r["projeto__nome"] or "-" for r in despesas_por_projeto]
    valores_despesas_projeto = [round(float(r["total"] or 0), 2) for r in despesas_por_projeto]

    # Fallback: se os filtros atuais não devolverem despesas, mostrar visão global da empresa
    # para evitar gráficos financeiros vazios.
    if not labels_despesas_dia and not labels_despesas_categoria and not labels_despesas_projeto:
        despesas_empresa = _filtrar_por_empresa(Despesa.objects.all(), empresa)
        despesas_por_dia = (
            despesas_empresa.values("data")
            .annotate(total=Sum("valor"))
            .order_by("data")
        )
        labels_despesas_dia = [r["data"].strftime("%d/%m/%Y") for r in despesas_por_dia]
        valores_despesas_dia = [round(float(r["total"] or 0), 2) for r in despesas_por_dia]

        despesas_por_categoria = (
            despesas_empresa.values("categoria")
            .annotate(total=Sum("valor"))
            .order_by("-total")
        )
        labels_despesas_categoria = [r["categoria"] or "sem categoria" for r in despesas_por_categoria]
        valores_despesas_categoria = [round(float(r["total"] or 0), 2) for r in despesas_por_categoria]

        despesas_por_projeto = (
            despesas_empresa.exclude(projeto__isnull=True)
            .values("projeto__nome")
            .annotate(total=Sum("valor"))
            .order_by("-total")[:10]
        )
        labels_despesas_projeto = [r["projeto__nome"] or "-" for r in despesas_por_projeto]
        valores_despesas_projeto = [round(float(r["total"] or 0), 2) for r in despesas_por_projeto]

    empregados_salario_qs = _filtrar_por_empresa(Empregados.objects.all(), empresa)
    if projeto_id:
        empregados_salario_qs = empregados_salario_qs.filter(
            Q(ligacoes_projetos__projeto_id=projeto_id)
            | Q(registos_diarios__projeto_id=projeto_id)
            | Q(ligacoes_furos__furo__projeto_id=projeto_id)
        )
    if empregado_id:
        empregados_salario_qs = empregados_salario_qs.filter(pk=empregado_id)
    empregados_salario = list(
        empregados_salario_qs.distinct().values("nome", "funcao", "salario")
    )
    salario_base_por_funcao = {
        item["funcao"]: float(item["salario_base"] or 0.0)
        for item in _filtrar_por_empresa(SalarioBaseFuncao.objects.all(), empresa).values("funcao", "salario_base")
    }

    mapa_funcoes = dict(Empregados.FUNCAO_GERAL_CHOICES)
    salarios_normalizados = []
    for item in empregados_salario:
        funcao_codigo = item.get("funcao") or "sem_funcao"
        funcao = mapa_funcoes.get(funcao_codigo, funcao_codigo if funcao_codigo != "sem_funcao" else "Sem função")
        salario_registado = float(item.get("salario") or 0.0)
        salario_base = float(salario_base_por_funcao.get(funcao_codigo, 0.0))
        salario_efetivo = salario_registado if salario_registado > 0 else salario_base
        salarios_normalizados.append(
            {
                "nome": item.get("nome") or "-",
                "funcao": funcao,
                "salario": round(salario_efetivo, 2),
            }
        )

    total_salarios_empregados = round(
        sum(item["salario"] for item in salarios_normalizados),
        2,
    )
    total_empregados_salario = len(salarios_normalizados)
    salario_medio_empregado = round(
        (total_salarios_empregados / total_empregados_salario) if total_empregados_salario else 0.0,
        2,
    )

    agregados_funcao = {}
    for item in salarios_normalizados:
        bucket = agregados_funcao.setdefault(
            item["funcao"],
            {"total": 0.0, "total_empregados": 0},
        )
        bucket["total"] += float(item["salario"] or 0.0)
        bucket["total_empregados"] += 1

    salarios_por_funcao = sorted(
        [
            {
                "funcao": funcao,
                "total": round(dados["total"], 2),
                "total_empregados": int(dados["total_empregados"]),
            }
            for funcao, dados in agregados_funcao.items()
        ],
        key=lambda x: x["total"],
        reverse=True,
    )
    labels_salarios_funcao = [item["funcao"] for item in salarios_por_funcao]
    valores_salarios_funcao = [item["total"] for item in salarios_por_funcao]
    quantidade_empregados_funcao = [item["total_empregados"] for item in salarios_por_funcao]

    salarios_por_empregado = sorted(
        salarios_normalizados,
        key=lambda x: float(x["salario"] or 0.0),
        reverse=True,
    )[:10]
    labels_salarios_empregado = [item["nome"] for item in salarios_por_empregado]
    valores_salarios_empregado = [item["salario"] for item in salarios_por_empregado]

    # Fallback: se filtros atuais não trouxerem salários, mostrar salários globais da empresa.
    if not labels_salarios_funcao and not labels_salarios_empregado:
        empregados_salario_empresa = list(
            _filtrar_por_empresa(Empregados.objects.all(), empresa)
            .values("nome", "funcao", "salario")
        )
        salarios_normalizados_empresa = []
        for item in empregados_salario_empresa:
            funcao_codigo = item.get("funcao") or "sem_funcao"
            funcao = mapa_funcoes.get(funcao_codigo, funcao_codigo if funcao_codigo != "sem_funcao" else "Sem função")
            salario_registado = float(item.get("salario") or 0.0)
            salario_base = float(salario_base_por_funcao.get(funcao_codigo, 0.0))
            salario_efetivo = salario_registado if salario_registado > 0 else salario_base
            salarios_normalizados_empresa.append(
                {
                    "nome": item.get("nome") or "-",
                    "funcao": funcao,
                    "salario": round(salario_efetivo, 2),
                }
            )

        agregados_funcao_empresa = {}
        for item in salarios_normalizados_empresa:
            bucket = agregados_funcao_empresa.setdefault(
                item["funcao"],
                {"total": 0.0, "total_empregados": 0},
            )
            bucket["total"] += float(item["salario"] or 0.0)
            bucket["total_empregados"] += 1

        salarios_por_funcao = sorted(
            [
                {
                    "funcao": funcao,
                    "total": round(dados["total"], 2),
                    "total_empregados": int(dados["total_empregados"]),
                }
                for funcao, dados in agregados_funcao_empresa.items()
            ],
            key=lambda x: x["total"],
            reverse=True,
        )
        labels_salarios_funcao = [item["funcao"] for item in salarios_por_funcao]
        valores_salarios_funcao = [item["total"] for item in salarios_por_funcao]
        quantidade_empregados_funcao = [item["total_empregados"] for item in salarios_por_funcao]

        salarios_por_empregado = sorted(
            salarios_normalizados_empresa,
            key=lambda x: float(x["salario"] or 0.0),
            reverse=True,
        )[:10]
        labels_salarios_empregado = [item["nome"] for item in salarios_por_empregado]
        valores_salarios_empregado = [item["salario"] for item in salarios_por_empregado]

    # Failsafe visual: evitar gráficos financeiros vazios.
    if not labels_despesas_dia:
        labels_despesas_dia = ["Sem dados"]
        valores_despesas_dia = [0.0]
    if not labels_despesas_categoria:
        labels_despesas_categoria = ["Sem dados"]
        valores_despesas_categoria = [0.0]
    if not labels_despesas_projeto:
        labels_despesas_projeto = ["Sem dados"]
        valores_despesas_projeto = [0.0]

    # Se não houver empregados, tentar mostrar salários base por função (se existirem).
    if not labels_salarios_funcao:
        salarios_base_lista = [
            (item["funcao"], float(item["salario_base"] or 0.0))
            for item in _filtrar_por_empresa(SalarioBaseFuncao.objects.all(), empresa).values("funcao", "salario_base")
            if float(item["salario_base"] or 0.0) > 0
        ]
        if salarios_base_lista:
            labels_salarios_funcao = [
                mapa_funcoes.get(funcao, funcao or "Sem função")
                for funcao, _ in salarios_base_lista
            ]
            valores_salarios_funcao = [round(valor, 2) for _, valor in salarios_base_lista]
            quantidade_empregados_funcao = [0 for _ in salarios_base_lista]
        else:
            labels_salarios_funcao = ["Sem dados"]
            valores_salarios_funcao = [0.0]
            quantidade_empregados_funcao = [0]

    if not labels_salarios_empregado:
        labels_salarios_empregado = ["Sem dados"]
        valores_salarios_empregado = [0.0]

    custo_cliente = 0.0
    if hasattr(empresa, "custo_por_metro_cliente"):
        custo_cliente = float(empresa.custo_por_metro_cliente or 0)
    resumos_projeto_financeiro, resumos_furo_financeiro = _obter_resumos_financeiros(
        empresa=empresa,
        projeto_id=projeto_id,
        custo_por_metro_cliente=custo_cliente,
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
        "labels_despesas_dia": labels_despesas_dia,
        "valores_despesas_dia": valores_despesas_dia,
        "labels_despesas_categoria": labels_despesas_categoria,
        "valores_despesas_categoria": valores_despesas_categoria,
        "labels_despesas_projeto": labels_despesas_projeto,
        "valores_despesas_projeto": valores_despesas_projeto,
        "labels_salarios_funcao": labels_salarios_funcao,
        "valores_salarios_funcao": valores_salarios_funcao,
        "quantidade_empregados_funcao": quantidade_empregados_funcao,
        "labels_salarios_empregado": labels_salarios_empregado,
        "valores_salarios_empregado": valores_salarios_empregado,
        "total_salarios_empregados": total_salarios_empregados,
        "total_empregados_salario": total_empregados_salario,
        "salario_medio_empregado": salario_medio_empregado,
        "resumos_projeto_financeiro": resumos_projeto_financeiro,
        "resumos_furo_financeiro": resumos_furo_financeiro,
        "labels": series_dia["labels_dia"],
        "dados_metros": series_dia["metros_dia"],
        "dados_horas": series_dia["horas_dia"],
        "dados_produtividade": series_dia["produtividade_dia"],
    }
