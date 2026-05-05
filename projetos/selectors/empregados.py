from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404

from projetos.models import (
    ConfiguracaoPerfuracaoEmpregado,
    DevolucaoMaterial,
    EmpregadoFuro,
    Empregados,
    Furo,
    Material,
    LevantamentoMaterial,
    Medicao,
    Projeto,
    RegistoDiarioEmpregado,
    MaquinaAvaria,
)



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _filtrar_por_empresa(queryset, empresa=None, campo="empresa_id"):
    if empresa is None:
        return queryset

    empresa_id = _resolver_empresa_id(empresa)
    return queryset.filter(**{campo: empresa_id})



def _obter_queryset_base_empregados():
    return Empregados.objects.all()



def _obter_dados_grafico_registos(registos_grafico):
    labels = []
    metros_por_dia = []
    horas_por_dia = []
    produtividade_por_dia = []
    agregados = {}

    for registo in registos_grafico:
        if not registo.data:
            continue

        chave = registo.data.strftime("%d/%m/%Y")

        if chave not in agregados:
            agregados[chave] = {
                "metros": 0,
                "horas": 0,
            }

        agregados[chave]["metros"] += registo.metros_furados or 0
        agregados[chave]["horas"] += registo.horas_trabalhadas or 0

    for data_label, valores in agregados.items():
        labels.append(data_label)
        metros = valores["metros"]
        horas = valores["horas"]
        produtividade = (metros / horas) if horas > 0 else 0

        metros_por_dia.append(round(metros, 2))
        horas_por_dia.append(round(horas, 2))
        produtividade_por_dia.append(round(produtividade, 2))

    return {
        "grafico_labels": labels,
        "grafico_metros": metros_por_dia,
        "grafico_horas": horas_por_dia,
        "grafico_produtividade": produtividade_por_dia,
    }



def _contexto_empregado_vazio(empregado):
    return {
        "empregado": empregado,
        "horas_hoje": 0,
        "horas_mes": 0,
        "horas_total": 0,
        "metros_hoje": 0,
        "metros_total": 0,
        "total_furos": 0,
        "media_metros_hora": 0,
        "media_metros_dia": 0,
        "ultimos_registos": empregado.registos_diarios.none(),
        "grafico_labels": [],
        "grafico_metros": [],
        "grafico_horas": [],
        "grafico_produtividade": [],
        "furos_trabalhados": Furo.objects.none(),
    }



def obter_lista_empregados(empresa=None):
    queryset = _obter_queryset_base_empregados().order_by("nome")
    return _filtrar_por_empresa(queryset, empresa)



def obter_empregados_pendentes(empresa=None):
    queryset = _obter_queryset_base_empregados().filter(aprovado=False).order_by("-data_registo")
    return _filtrar_por_empresa(queryset, empresa)



def obter_contexto_area_empregado(empregado, empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    if empresa_id is not None and empregado.empresa_id != empresa_id:
        return _contexto_empregado_vazio(empregado)

    furos_trabalhados = Furo.objects.filter(registos_furo__empregado=empregado).distinct()
    ultimos_registos_qs = empregado.registos_diarios.select_related("projeto", "furo")
    registos_grafico = empregado.registos_diarios.order_by("data", "criado_em")

    if empresa_id is not None:
        furos_trabalhados = furos_trabalhados.filter(empresa_id=empresa_id)
        ultimos_registos_qs = ultimos_registos_qs.filter(empresa_id=empresa_id)
        registos_grafico = registos_grafico.filter(empresa_id=empresa_id)

    ultimos_registos = ultimos_registos_qs[:5]

    dados_grafico = _obter_dados_grafico_registos(registos_grafico)

    return {
        "empregado": empregado,
        "horas_hoje": empregado.horas_diarias or 0,
        "horas_mes": empregado.horas_trabalhadas_mes or 0,
        "horas_total": empregado.horas_total or 0,
        "metros_hoje": empregado.metros_furados_hoje or 0,
        "metros_total": empregado.total_metros_furados or 0,
        "total_furos": empregado.total_furos_trabalhados or 0,
        "media_metros_hora": empregado.media_metros_por_hora or 0,
        "media_metros_dia": empregado.media_metros_por_dia or 0,
        "ultimos_registos": ultimos_registos,
        "furos_trabalhados": furos_trabalhados,
        **dados_grafico,
    }


def obter_furo_empregado(pk, empregado):
    return Furo.objects.select_related("projeto").filter(pk=pk, empresa=empregado.empresa).first()


def empregado_tem_acesso_furo(empregado, furo):
    associado = EmpregadoFuro.objects.filter(
        empregado=empregado,
        furo=furo,
        empresa=empregado.empresa,
    ).exists()
    com_registos = RegistoDiarioEmpregado.objects.filter(
        empregado=empregado,
        furo=furo,
        empresa=empregado.empresa,
    ).exists()
    return associado or com_registos


def obter_medicoes_furo_empregado(empregado, furo):
    return Medicao.objects.filter(
        furo=furo,
        empresa=empregado.empresa,
    ).order_by("criado_em", "profundidade_medida")


def obter_registos_furo_empregado(empregado, furo):
    return RegistoDiarioEmpregado.objects.filter(
        empregado=empregado,
        furo=furo,
        empresa=empregado.empresa,
    ).select_related("projeto", "furo").order_by("-data", "-criado_em")


def obter_levantamentos_furo_empregado(empregado, furo):
    return (
        LevantamentoMaterial.objects.filter(
            empregado=empregado,
            furo=furo,
            empresa=empregado.empresa,
        )
        .select_related("material", "projeto", "furo")
        .order_by("-data", "-criado_em")
    )


def obter_levantamentos_furo_empresa(empregado, furo):
    return (
        LevantamentoMaterial.objects.filter(
            furo=furo,
            empresa=empregado.empresa,
        )
        .select_related("empregado", "material", "projeto", "furo")
        .order_by("-data", "-criado_em")
    )


def obter_devolucoes_furo_empregado(empregado, furo):
    return (
        DevolucaoMaterial.objects.filter(
            empregado=empregado,
            furo=furo,
            empresa=empregado.empresa,
        )
        .select_related("material", "projeto", "furo")
        .order_by("-data", "-criado_em")
    )


def obter_devolucoes_furo_empresa(empregado, furo):
    return (
        DevolucaoMaterial.objects.filter(
            furo=furo,
            empresa=empregado.empresa,
        )
        .select_related("empregado", "material", "projeto", "furo")
        .order_by("-data", "-criado_em")
    )


def obter_lista_furos_empregado(empregado):
    furo_ids_associados = EmpregadoFuro.objects.filter(
        empregado=empregado,
        empresa=empregado.empresa,
    ).values_list("furo_id", flat=True)

    furo_ids_registos = empregado.registos_diarios.filter(
        furo__isnull=False,
        empresa=empregado.empresa,
    ).values_list("furo_id", flat=True)

    return Furo.objects.select_related("projeto").filter(
        empresa=empregado.empresa,
        id__in=list(furo_ids_associados) + list(furo_ids_registos),
    ).distinct().order_by("nome")


def obter_lista_medicoes_empregado(
    empregado,
    *,
    furo_id=None,
    nome_furo=None,
    projeto_id=None,
    profundidade_min=None,
    profundidade_max=None,
):
    # Geólogo deve conseguir consultar todas as medições da empresa.
    if (empregado.funcao or "").strip().lower() == "geologo":
        qs = (
            Medicao.objects.filter(empresa=empregado.empresa)
            .select_related("furo", "furo__projeto")
        )
    else:
        furos_associados_ids = empregado.ligacoes_furos.filter(
            empresa=empregado.empresa,
            ativo=True,
        ).values_list("furo_id", flat=True)

        furos_com_registos_ids = empregado.registos_diarios.filter(
            empresa=empregado.empresa,
        ).exclude(furo__isnull=True).values_list("furo_id", flat=True)

        qs = (
            Medicao.objects.filter(
                empresa=empregado.empresa,
                furo_id__in=set(furos_associados_ids).union(set(furos_com_registos_ids)),
            )
            .select_related("furo", "furo__projeto")
        )

    if furo_id:
        qs = qs.filter(furo_id=furo_id)

    if projeto_id:
        qs = qs.filter(furo__projeto_id=projeto_id)

    if nome_furo:
        nome_furo = nome_furo.strip()
        if nome_furo:
            qs = qs.filter(
                Q(nome_furo_snapshot__icontains=nome_furo)
                | Q(furo__nome__icontains=nome_furo)
            )

    if profundidade_min not in (None, ""):
        qs = qs.filter(profundidade_medida__gte=profundidade_min)

    if profundidade_max not in (None, ""):
        qs = qs.filter(profundidade_medida__lte=profundidade_max)

    return qs.order_by("-criado_em", "-profundidade_medida")


def obter_medicao_empregado(pk, empregado):
    return Medicao.objects.select_related("furo", "furo__projeto").filter(
        pk=pk,
        empresa=empregado.empresa,
    ).first()


def obter_lista_projetos_empregado(empregado):
    projetos_associados_ids = empregado.ligacoes_projetos.filter(
        empresa=empregado.empresa,
    ).values_list("projeto_id", flat=True)

    projetos_registos_ids = empregado.registos_diarios.filter(
        projeto__isnull=False,
        empresa=empregado.empresa,
    ).values_list("projeto_id", flat=True)

    return Projeto.objects.filter(
        empresa=empregado.empresa,
        id__in=list(projetos_associados_ids) + list(projetos_registos_ids),
    ).distinct().annotate(
        total_furos_projeto=Count("furos", distinct=True)
    ).order_by("nome")


def obter_resumo_registos_projetos_empregado(empregado, projetos):
    resumo_registos = (
        empregado.registos_diarios
        .filter(projeto__in=projetos, empresa=empregado.empresa)
        .values("projeto_id")
        .annotate(
            total_metros=Sum("metros_furados"),
            total_horas=Sum("horas_trabalhadas"),
        )
    )
    return {item["projeto_id"]: item for item in resumo_registos}


def obter_projeto_empregado(pk, empregado):
    return Projeto.objects.filter(pk=pk, empresa=empregado.empresa).first()


def empregado_tem_acesso_projeto(empregado, projeto):
    associado = empregado.ligacoes_projetos.filter(
        projeto=projeto,
        empresa=empregado.empresa,
    ).exists()
    com_registos = empregado.registos_diarios.filter(
        projeto=projeto,
        empresa=empregado.empresa,
    ).exists()
    return associado or com_registos


def obter_furos_projeto_empregado(empregado, projeto):
    furo_ids_associados = EmpregadoFuro.objects.filter(
        empregado=empregado,
        empresa=empregado.empresa,
        furo__projeto=projeto,
    ).values_list("furo_id", flat=True)

    furo_ids_registos = empregado.registos_diarios.filter(
        projeto=projeto,
        furo__isnull=False,
        empresa=empregado.empresa,
    ).values_list("furo_id", flat=True)

    return Furo.objects.filter(
        empresa=empregado.empresa,
        projeto=projeto,
        id__in=list(furo_ids_associados) + list(furo_ids_registos),
    ).distinct().order_by("nome")


def obter_trabalhadores_envolvidos_projeto_empregado(empregado, projeto):
    return projeto.empregado_projetos.select_related("empregado").filter(
        empresa=empregado.empresa,
        ativo=True,
    ).order_by("empregado__nome")


def obter_registos_projeto_empregado(empregado, projeto):
    return empregado.registos_diarios.filter(projeto=projeto, empresa=empregado.empresa)


def obter_historico_projetos_empregado_area(empregado):
    return (
        empregado.ligacoes_projetos
        .select_related("projeto")
        .filter(empresa=empregado.empresa)
        .order_by("-ativo", "-data_inicio")
    )


def obter_resumo_furos_empregado_area(empregado):
    return (
        RegistoDiarioEmpregado.objects
        .filter(
            empregado=empregado,
            empresa=empregado.empresa,
            furo__isnull=False,
        )
        .values("furo__id", "furo__nome", "projeto__nome")
        .annotate(
            total_metros=Sum("metros_furados"),
            total_horas=Sum("horas_trabalhadas"),
        )
        .order_by("-total_metros", "furo__nome")
    )


def obter_totais_empregado_area(empregado):
    return {
        "total_registos": RegistoDiarioEmpregado.objects.filter(
            empregado=empregado,
            empresa=empregado.empresa,
        ).count(),
        "total_levantamentos": LevantamentoMaterial.objects.filter(
            empregado=empregado,
            empresa=empregado.empresa,
        ).count(),
        "total_devolucoes": DevolucaoMaterial.objects.filter(
            empregado=empregado,
            empresa=empregado.empresa,
        ).count(),
        "total_configuracoes": ConfiguracaoPerfuracaoEmpregado.objects.filter(
            empregado=empregado,
            empresa=empregado.empresa,
        ).count(),
    }


def obter_empregado_admin_por_pk(pk, empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return get_object_or_404(Empregados, pk=pk, empresa_id=empresa_id)


def obter_medias_operacionais_empregado(empregado, empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else empregado.empresa_id
    qs = RegistoDiarioEmpregado.objects.filter(
        empregado=empregado,
        empresa_id=empresa_id,
    )

    total_metros = float(qs.aggregate(total=Sum("metros_furados")).get("total") or 0.0)
    total_horas = float(qs.aggregate(total=Sum("horas_trabalhadas")).get("total") or 0.0)

    dias_distintos = qs.values("data").distinct().count()
    furos_distintos = qs.exclude(furo__isnull=True).values("furo_id").distinct().count()
    projetos_distintos = qs.exclude(projeto__isnull=True).values("projeto_id").distinct().count()

    horas_por_semana = (
        qs.exclude(data__isnull=True)
        .values("data__year", "data__week")
        .annotate(total=Sum("horas_trabalhadas"))
    )
    horas_por_mes = (
        qs.exclude(data__isnull=True)
        .values("data__year", "data__month")
        .annotate(total=Sum("horas_trabalhadas"))
    )
    horas_por_ano = (
        qs.exclude(data__isnull=True)
        .values("data__year")
        .annotate(total=Sum("horas_trabalhadas"))
    )

    total_semanas = len(horas_por_semana)
    total_meses = len(horas_por_mes)
    total_anos = len(horas_por_ano)

    media_metros_por_dia = round(total_metros / dias_distintos, 2) if dias_distintos else 0.0
    media_metros_por_furo = round(total_metros / furos_distintos, 2) if furos_distintos else 0.0
    media_metros_por_projeto = round(total_metros / projetos_distintos, 2) if projetos_distintos else 0.0

    media_horas_por_dia = round(total_horas / dias_distintos, 2) if dias_distintos else 0.0
    media_horas_semanais = round(total_horas / total_semanas, 2) if total_semanas else 0.0
    media_horas_mensais = round(total_horas / total_meses, 2) if total_meses else 0.0
    media_horas_anuais = round(total_horas / total_anos, 2) if total_anos else 0.0

    return {
        "media_metros_por_dia": media_metros_por_dia,
        "media_metros_por_furo": media_metros_por_furo,
        "media_metros_por_projeto": media_metros_por_projeto,
        "media_horas_por_dia": media_horas_por_dia,
        "media_horas_semanais": media_horas_semanais,
        "media_horas_mensais": media_horas_mensais,
        "media_horas_anuais": media_horas_anuais,
        "dias_com_registo": dias_distintos,
        "furos_com_registo": furos_distintos,
        "projetos_com_registo": projetos_distintos,
    }


def obter_avarias_empregado(empregado, empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else empregado.empresa_id
    qs = (
        MaquinaAvaria.objects.select_related("maquina", "projeto", "furo", "reportado_por")
        .filter(
            empresa_id=empresa_id,
            responsavel_empregado=empregado,
        )
        .order_by("-data_inicio", "-criado_em")
    )
    return {
        "avarias_atribuidas": qs,
        "total_avarias_atribuidas": qs.count(),
        "total_avarias_resolvidas": qs.filter(status="resolvida").count(),
        "total_avarias_abertas": qs.filter(status__in=["aberta", "em_reparacao"]).count(),
    }


def obter_ligacao_projeto_empregado_admin(ligacao_id, empregado, empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return get_object_or_404(
        empregado.ligacoes_projetos,
        id=ligacao_id,
        empregado=empregado,
        empresa_id=empresa_id,
    )


def obter_ficheiro_empregado_admin(ficheiro_id, empregado, empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return get_object_or_404(
        empregado.ficheiros,
        id=ficheiro_id,
        empregado=empregado,
        empresa_id=empresa_id,
    )


def obter_empregado_pendente_admin_por_pk(pk, empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return get_object_or_404(Empregados, pk=pk, empresa_id=empresa_id, aprovado=False)


def obter_contexto_materiais_disponiveis_empregado(
    empregado,
    *,
    projeto_id="",
    furo_id="",
    nome="",
    incluir_todos_empresa=False,
):
    projetos_ids = list(
        empregado.ligacoes_projetos.filter(empresa=empregado.empresa).values_list("projeto_id", flat=True)
    )

    furos_ids_associados = list(
        empregado.ligacoes_furos.filter(
            empresa=empregado.empresa,
        ).values_list("furo_id", flat=True)
    )

    furos_ids_registos = list(
        empregado.registos_diarios.filter(
            furo__isnull=False,
            empresa=empregado.empresa,
        ).values_list("furo_id", flat=True)
    )
    furos_ids = list(set(furos_ids_associados + furos_ids_registos))

    materiais = Material.objects.filter(ativo=True)
    if empregado.empresa_id:
        materiais = materiais.filter(empresa=empregado.empresa)

    if not incluir_todos_empresa:
        materiais = materiais.filter(
            Q(projeto_id__in=projetos_ids) | Q(furo_id__in=furos_ids)
        ).distinct()

    if projeto_id:
        materiais = materiais.filter(projeto_id=projeto_id)
    if furo_id:
        materiais = materiais.filter(furo_id=furo_id)
    if nome:
        materiais = materiais.filter(nome__icontains=nome)
    materiais = materiais.select_related("projeto", "furo").order_by("nome")

    if incluir_todos_empresa:
        projetos = Projeto.objects.filter(empresa=empregado.empresa).distinct().order_by("nome")
        furos = Furo.objects.filter(empresa=empregado.empresa).distinct().order_by("nome")
    else:
        projetos = Projeto.objects.filter(
            empresa=empregado.empresa,
            id__in=projetos_ids,
        ).distinct().order_by("nome")
        furos = Furo.objects.filter(
            empresa=empregado.empresa,
            id__in=furos_ids,
        ).distinct().order_by("nome")

    return {
        "materiais": materiais,
        "projetos": projetos,
        "furos": furos,
    }


def obter_furo_admin_por_pk_empresa(pk, empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return get_object_or_404(Furo, pk=pk, empresa_id=empresa_id)


def obter_ligacao_empregado_furo_admin_por_pk(pk, empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return get_object_or_404(
        EmpregadoFuro.objects.select_related("furo", "empregado"),
        pk=pk,
        empresa_id=empresa_id,
    )
