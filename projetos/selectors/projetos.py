from django.shortcuts import get_object_or_404

from projetos.models import Medicao, Projeto


# TODO futuro:
# - centralizar filtros multiempresa num helper/base selector reutilizável
# - adicionar paginação/otimização quando o volume de projetos crescer
# - avaliar cache nas consultas de mapa e detalhe


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _filtrar_queryset_por_empresa(queryset, empresa=None, campo_empresa="empresa_id"):
    if empresa is None:
        return queryset

    empresa_id = _resolver_empresa_id(empresa)
    return queryset.filter(**{campo_empresa: empresa_id})



def _decimal_para_float(valor):
    return float(valor) if valor is not None else None



def _serializar_projeto_mapa(projeto):
    return {
        "id": str(projeto.id),
        "nome": projeto.nome,
        "cidade": projeto.cidade,
        "pais": projeto.pais,
        "status": projeto.status,
        "localizacao_lat": _decimal_para_float(projeto.localizacao_lat),
        "localizacao_lon": _decimal_para_float(projeto.localizacao_lon),
    }



def _serializar_furo_mapa(furo):
    if furo.latitude is None or furo.longitude is None:
        return None

    return {
        "id": str(furo.id),
        "nome": furo.nome,
        "profundidade_atual": furo.profundidade_atual or 0,
        "profundidade_alvo_inicial": furo.profundidade_alvo_inicial or 0,
        "profundidade_alvo_atual": furo.profundidade_alvo_atual or 0,
        "inclinacao_planeada_inicial": (
            furo.inclinacao_planeada_inicial
            if furo.inclinacao_planeada_inicial is not None else "-"
        ),
        "azimute_planeado_inicial": (
            furo.azimute_planeado_inicial
            if furo.azimute_planeado_inicial is not None else "-"
        ),
        "lat": _decimal_para_float(furo.latitude),
        "lon": _decimal_para_float(furo.longitude),
    }



def _serializar_furo_3d(furo):
    return {
        "id": str(furo.id),
        "nome": furo.nome,
        "origem_este": furo.origem_este or 0,
        "origem_norte": furo.origem_norte or 0,
        "origem_tvd": furo.origem_tvd or 0,
        "profundidade_inicial": furo.profundidade_inicial or 0,
        "profundidade_atual": furo.profundidade_atual or 0,
        "profundidade_maxima_atingida": furo.profundidade_maxima_atingida or 0,
        "profundidade_alvo_inicial": furo.profundidade_alvo_inicial or 0,
        "profundidade_alvo_atual": furo.profundidade_alvo_atual or 0,
        "inclinacao_planeada_inicial": furo.inclinacao_planeada_inicial or 0,
        "inclinacao_planeada_atual": furo.inclinacao_planeada_atual or 0,
        "azimute_planeado_inicial": furo.azimute_planeado_inicial or 0,
        "azimute_planeado_atual": furo.azimute_planeado_atual or 0,
        "inclinacao_real_atual": furo.inclinacao_real_atual or 0,
        "azimute_real_atual": furo.azimute_real_atual or 0,
        "estado": furo.estado,
    }



def obter_projetos_mapa(empresa=None):
    projetos_qs = _filtrar_queryset_por_empresa(
        Projeto.objects.all().order_by("nome"),
        empresa=empresa,
    )
    return [_serializar_projeto_mapa(projeto) for projeto in projetos_qs]



def obter_lista_projetos(empresa=None):
    queryset = Projeto.objects.all().order_by("nome")
    return _filtrar_queryset_por_empresa(queryset, empresa=empresa)



def obter_projeto(pk, empresa=None):
    queryset = _filtrar_queryset_por_empresa(Projeto.objects.all(), empresa=empresa)
    return get_object_or_404(queryset, pk=pk)



def obter_contexto_projeto_detail(pk, empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    queryset = Projeto.objects.prefetch_related(
        "furos",
        "materiais",
        "maquinas",
        "levantamentos_materiais",
        "registos_projeto",
    )
    queryset = _filtrar_queryset_por_empresa(queryset, empresa=empresa)

    projeto = get_object_or_404(queryset, pk=pk)

    furos = projeto.furos.all().order_by("nome")
    if empresa_id is not None:
        furos = furos.filter(empresa_id=empresa_id)

    furos_mapa = []
    for furo in furos:
        furo_mapa = _serializar_furo_mapa(furo)
        if furo_mapa is not None:
            furos_mapa.append(furo_mapa)

    levantamentos = projeto.levantamentos_materiais.select_related(
        "empregado", "material", "furo"
    ).all()
    registos = projeto.registos_projeto.select_related("empregado", "furo").all()
    materiais = projeto.materiais.all()
    maquinas = projeto.maquinas.all()

    if empresa_id is not None:
        levantamentos = levantamentos.filter(empresa_id=empresa_id)
        registos = registos.filter(empresa_id=empresa_id)
        materiais = materiais.filter(empresa_id=empresa_id)
        maquinas = maquinas.filter(empresa_id=empresa_id)

    return {
        "projeto": projeto,
        "furos": furos,
        "furos_mapa": furos_mapa,
        "levantamentos": levantamentos,
        "materiais": materiais,
        "maquinas": maquinas,
        "registos": registos,
        "projeto_mapa": {
            "nome": projeto.nome,
            "cidade": projeto.cidade,
            "pais": projeto.pais,
            "lat": _decimal_para_float(projeto.localizacao_lat),
            "lon": _decimal_para_float(projeto.localizacao_lon),
        },
    }



def obter_furos_projeto(projeto, empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    if empresa_id is not None and projeto.empresa_id != empresa_id:
        return projeto.furos.none()

    queryset = projeto.furos.all().order_by("nome")

    if empresa_id is not None:
        queryset = queryset.filter(empresa_id=empresa_id)

    return queryset



def obter_medicoes_projeto(projeto, empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    if empresa_id is not None and projeto.empresa_id != empresa_id:
        return Medicao.objects.none()

    queryset = (
        Medicao.objects.filter(furo__projeto=projeto)
        .select_related("furo")
        .order_by("criado_em", "profundidade_medida")
    )

    if empresa_id is not None:
        queryset = queryset.filter(
            empresa_id=empresa_id,
            furo__empresa_id=empresa_id,
        )

    return queryset



def obter_dados_3d_projeto(projeto, empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    if empresa_id is not None and projeto.empresa_id != empresa_id:
        return []

    furos = projeto.furos.all().order_by("nome")

    if empresa_id is not None:
        furos = furos.filter(empresa_id=empresa_id)

    return [_serializar_furo_3d(furo) for furo in furos]