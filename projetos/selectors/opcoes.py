from django.db.models import Q

from projetos.models import (
    Despesa,
    Empregados,
    EventoAnalytics,
    Furo,
    Maquina,
    Material,
    Medicao,
    Projeto,
    RegistoDiarioEmpregado,
)


def _empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def obter_projeto_furo_filtros_exportacao(*, empresa, projeto_id=None, furo_id=None):
    projeto = None
    furo = None

    if projeto_id:
        projeto = Projeto.objects.filter(empresa=empresa, pk=projeto_id).first()

    if furo_id:
        furo_queryset = Furo.objects.filter(empresa=empresa, pk=furo_id)
        if projeto:
            furo_queryset = furo_queryset.filter(projeto=projeto)
        furo = furo_queryset.first()

    return projeto, furo


def _filtrar_periodo_queryset(queryset, campo, *, data_inicio=None, data_fim=None):
    if data_inicio:
        queryset = queryset.filter(**{f"{campo}__gte": data_inicio})
    if data_fim:
        queryset = queryset.filter(**{f"{campo}__lte": data_fim})
    return queryset


def qs_projetos_exportacao(*, empresa, projeto=None, data_inicio=None, data_fim=None):
    queryset = Projeto.objects.filter(empresa=empresa)
    if projeto:
        queryset = queryset.filter(pk=projeto.pk)
    return _filtrar_periodo_queryset(queryset, "data_inicio_proj", data_inicio=data_inicio, data_fim=data_fim)


def qs_furos_exportacao(*, empresa, projeto=None, furo=None, data_inicio=None, data_fim=None):
    queryset = Furo.objects.filter(empresa=empresa)
    if projeto:
        queryset = queryset.filter(projeto=projeto)
    if furo:
        queryset = queryset.filter(pk=furo.pk)
    return _filtrar_periodo_queryset(queryset, "data__date", data_inicio=data_inicio, data_fim=data_fim)


def qs_maquinas_exportacao(*, empresa, projeto=None, furo=None, data_inicio=None, data_fim=None):
    queryset = Maquina.objects.filter(empresa=empresa)
    if projeto:
        queryset = queryset.filter(Q(projeto_atual=projeto) | Q(projetos=projeto)).distinct()
    if furo:
        queryset = queryset.filter(furos=furo).distinct()
    return _filtrar_periodo_queryset(queryset, "data_registo", data_inicio=data_inicio, data_fim=data_fim)


def qs_materiais_exportacao(*, empresa, projeto=None, furo=None, data_inicio=None, data_fim=None):
    queryset = Material.objects.filter(empresa=empresa)
    if projeto:
        queryset = queryset.filter(Q(projeto=projeto) | Q(furo__projeto=projeto)).distinct()
    if furo:
        queryset = queryset.filter(furo=furo)
    return _filtrar_periodo_queryset(queryset, "data_compra", data_inicio=data_inicio, data_fim=data_fim)


def qs_empregados_exportacao(*, empresa, projeto=None, furo=None, data_inicio=None, data_fim=None):
    queryset = Empregados.objects.filter(empresa=empresa)
    if projeto:
        queryset = queryset.filter(ligacoes_projetos__projeto=projeto).distinct()
    if furo:
        queryset = queryset.filter(Q(furos=furo) | Q(ligacoes_furos__furo=furo)).distinct()
    return _filtrar_periodo_queryset(queryset, "data_admissao", data_inicio=data_inicio, data_fim=data_fim)


def qs_registos_exportacao(
    *,
    empresa,
    projeto=None,
    furo=None,
    tipo_registo="",
    data_inicio=None,
    data_fim=None,
):
    queryset = RegistoDiarioEmpregado.objects.filter(empresa=empresa)
    if projeto:
        queryset = queryset.filter(projeto=projeto)
    if furo:
        queryset = queryset.filter(furo=furo)
    if tipo_registo == "sem_paragem":
        queryset = queryset.filter(tipo_paragem="")
    elif tipo_registo:
        queryset = queryset.filter(tipo_paragem=tipo_registo)
    return _filtrar_periodo_queryset(queryset, "data", data_inicio=data_inicio, data_fim=data_fim)


def qs_medicoes_exportacao(*, empresa, projeto=None, furo=None, data_inicio=None, data_fim=None):
    queryset = Medicao.objects.filter(empresa=empresa)
    if projeto:
        queryset = queryset.filter(furo__projeto=projeto)
    if furo:
        queryset = queryset.filter(furo=furo)
    return _filtrar_periodo_queryset(queryset, "criado_em__date", data_inicio=data_inicio, data_fim=data_fim)


def qs_despesas_exportacao(
    *,
    empresa,
    projeto=None,
    furo=None,
    categoria_despesa="",
    data_inicio=None,
    data_fim=None,
):
    queryset = Despesa.objects.filter(empresa=empresa)
    if projeto:
        queryset = queryset.filter(Q(projeto=projeto) | Q(furo__projeto=projeto) | Q(maquina__projetos=projeto)).distinct()
    if furo:
        queryset = queryset.filter(Q(furo=furo) | Q(projeto=furo.projeto) | Q(maquina__furos=furo)).distinct()
    if categoria_despesa:
        queryset = queryset.filter(categoria=categoria_despesa)
    return _filtrar_periodo_queryset(queryset, "data", data_inicio=data_inicio, data_fim=data_fim)


def qs_eventos_exportacao(*, empresa, projeto=None, furo=None, data_inicio=None, data_fim=None):
    queryset = EventoAnalytics.objects.filter(empresa=empresa)
    if projeto:
        queryset = queryset.filter(Q(projeto=projeto) | Q(furo__projeto=projeto)).distinct()
    if furo:
        queryset = queryset.filter(furo=furo)
    return _filtrar_periodo_queryset(queryset, "criado_em__date", data_inicio=data_inicio, data_fim=data_fim)


def listar_projetos_filtro_exportacao(empresa):
    return Projeto.objects.filter(empresa=empresa).order_by("nome")


def listar_furos_filtro_exportacao(*, empresa, projeto=None):
    return qs_furos_exportacao(empresa=empresa, projeto=projeto).order_by("nome")


def obter_resultados_procurar_dashboard(empresa, termo):
    empresa_id = _empresa_id(empresa)
    resultados = {
        "projetos": Projeto.objects.none(),
        "furos": Furo.objects.none(),
        "empregados": Empregados.objects.none(),
        "maquinas": Maquina.objects.none(),
        "materiais": Material.objects.none(),
        "registos": RegistoDiarioEmpregado.objects.none(),
        "medicoes": Medicao.objects.none(),
        "despesas": Despesa.objects.none(),
        "eventos": EventoAnalytics.objects.none(),
    }
    totais = {chave: 0 for chave in resultados}

    if not termo:
        return resultados, totais

    filtros_projetos = (
        Q(nome__icontains=termo)
        | Q(cliente__icontains=termo)
        | Q(cidade__icontains=termo)
        | Q(pais__icontains=termo)
        | Q(notas__icontains=termo)
    )
    filtros_furos = (
        Q(nome__icontains=termo)
        | Q(localizacao__icontains=termo)
        | Q(local_sondagem__icontains=termo)
        | Q(detalhes__icontains=termo)
    )
    filtros_empregados = (
        Q(nome__icontains=termo)
        | Q(email__icontains=termo)
        | Q(telefone__icontains=termo)
        | Q(funcao__icontains=termo)
        | Q(morada__icontains=termo)
    )
    filtros_maquinas = (
        Q(nome__icontains=termo)
        | Q(tipo__icontains=termo)
        | Q(marca__icontains=termo)
        | Q(modelo__icontains=termo)
        | Q(numero_serie__icontains=termo)
        | Q(matricula__icontains=termo)
        | Q(localizacao_atual__icontains=termo)
    )
    filtros_materiais = (
        Q(nome__icontains=termo)
        | Q(tipo__icontains=termo)
        | Q(marca__icontains=termo)
        | Q(numero_serie__icontains=termo)
        | Q(fornecedor__icontains=termo)
        | Q(localizacao__icontains=termo)
        | Q(observacoes__icontains=termo)
    )
    filtros_registos = (
        Q(observacoes__icontains=termo)
        | Q(empregado__nome__icontains=termo)
        | Q(projeto__nome__icontains=termo)
        | Q(furo__nome__icontains=termo)
    )
    filtros_medicoes = (
        Q(nome_furo_snapshot__icontains=termo)
        | Q(tipo_rocha__icontains=termo)
        | Q(observacoes__icontains=termo)
        | Q(furo__nome__icontains=termo)
    )
    filtros_despesas = (
        Q(descricao__icontains=termo)
        | Q(tipo__icontains=termo)
        | Q(categoria__icontains=termo)
        | Q(observacoes__icontains=termo)
    )
    filtros_eventos = (
        Q(entidade_tipo__icontains=termo)
        | Q(entidade_label__icontains=termo)
        | Q(actor_username__icontains=termo)
    )

    resultados["projetos"] = (
        Projeto.objects.filter(empresa_id=empresa_id).filter(filtros_projetos).order_by("nome")[:12]
    )
    resultados["furos"] = (
        Furo.objects.filter(empresa_id=empresa_id)
        .select_related("projeto")
        .filter(filtros_furos)
        .order_by("nome")[:12]
    )
    resultados["empregados"] = (
        Empregados.objects.filter(empresa_id=empresa_id).filter(filtros_empregados).order_by("nome")[:12]
    )
    resultados["maquinas"] = (
        Maquina.objects.filter(empresa_id=empresa_id).filter(filtros_maquinas).order_by("nome")[:12]
    )
    resultados["materiais"] = (
        Material.objects.filter(empresa_id=empresa_id)
        .select_related("projeto", "furo")
        .filter(filtros_materiais)
        .order_by("nome")[:12]
    )
    resultados["registos"] = (
        RegistoDiarioEmpregado.objects.filter(empresa_id=empresa_id)
        .select_related("empregado", "projeto", "furo")
        .filter(filtros_registos)
        .order_by("-data", "-criado_em")[:12]
    )
    resultados["medicoes"] = (
        Medicao.objects.filter(empresa_id=empresa_id)
        .select_related("furo")
        .filter(filtros_medicoes)
        .order_by("-criado_em")[:12]
    )
    resultados["despesas"] = (
        Despesa.objects.filter(empresa_id=empresa_id)
        .select_related("projeto", "furo", "maquina")
        .filter(filtros_despesas)
        .order_by("-data", "-criado_em")[:12]
    )
    resultados["eventos"] = (
        EventoAnalytics.objects.filter(empresa_id=empresa_id)
        .select_related("projeto", "furo", "empregado", "material", "maquina")
        .filter(filtros_eventos)
        .order_by("-criado_em")[:20]
    )

    totais = {
        "projetos": Projeto.objects.filter(empresa_id=empresa_id).filter(filtros_projetos).count(),
        "furos": Furo.objects.filter(empresa_id=empresa_id).filter(filtros_furos).count(),
        "empregados": Empregados.objects.filter(empresa_id=empresa_id).filter(filtros_empregados).count(),
        "maquinas": Maquina.objects.filter(empresa_id=empresa_id).filter(filtros_maquinas).count(),
        "materiais": Material.objects.filter(empresa_id=empresa_id).filter(filtros_materiais).count(),
        "registos": RegistoDiarioEmpregado.objects.filter(empresa_id=empresa_id).filter(filtros_registos).count(),
        "medicoes": Medicao.objects.filter(empresa_id=empresa_id).filter(filtros_medicoes).count(),
        "despesas": Despesa.objects.filter(empresa_id=empresa_id).filter(filtros_despesas).count(),
        "eventos": EventoAnalytics.objects.filter(empresa_id=empresa_id).filter(filtros_eventos).count(),
    }
    return resultados, totais
