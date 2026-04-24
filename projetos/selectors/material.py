from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from projetos.models import DevolucaoMaterial, Empregados, LevantamentoMaterial, Material, Projeto



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _filtrar_por_empresa(queryset, empresa=None, campo="empresa_id"):
    if empresa is None:
        return queryset

    empresa_id = _resolver_empresa_id(empresa)
    return queryset.filter(**{campo: empresa_id})



def _filtrar_movimentos_material_por_empresa(queryset, empresa=None):
    if empresa is None:
        return queryset

    empresa_id = _resolver_empresa_id(empresa)
    return queryset.filter(
        empresa_id=empresa_id,
        material__empresa_id=empresa_id,
    )



def _obter_queryset_base_materiais():
    return Material.objects.select_related("projeto", "furo")



def _obter_queryset_base_levantamentos():
    return LevantamentoMaterial.objects.select_related(
        "empregado",
        "material",
        "projeto",
        "furo",
    )



def _obter_queryset_base_devolucoes():
    return DevolucaoMaterial.objects.select_related(
        "empregado",
        "material",
        "projeto",
        "furo",
    )



def obter_lista_materiais(empresa=None):
    queryset = _obter_queryset_base_materiais().order_by("nome")
    return _filtrar_por_empresa(queryset, empresa)


def obter_lista_materiais_filtrada_nome(*, empresa=None, nome=""):
    queryset = obter_lista_materiais(empresa=empresa)
    nome = (nome or "").strip()
    if nome:
        queryset = queryset.filter(nome__icontains=nome)
    return queryset



def obter_material(material_id, empresa=None):
    queryset = _obter_queryset_base_materiais()
    queryset = _filtrar_por_empresa(queryset, empresa)
    return get_object_or_404(queryset, pk=material_id)


def obter_material_por_id_empresa(material_id, empresa):
    return get_object_or_404(_obter_queryset_base_materiais(), id=material_id, empresa_id=_resolver_empresa_id(empresa))


def obter_material_por_id_empresa_select_for_update(material_id, empresa):
    return get_object_or_404(
        Material.objects.select_for_update(),
        id=material_id,
        empresa_id=_resolver_empresa_id(empresa),
    )



def obter_contexto_material_detail(material_id, empresa=None):
    material = obter_material(material_id, empresa=empresa)

    levantamentos = material.levantamentos.select_related(
        "empregado",
        "projeto",
        "furo",
    ).all()
    devolucoes = material.devolucoes.select_related(
        "empregado",
        "projeto",
        "furo",
    ).all()

    levantamentos = _filtrar_por_empresa(levantamentos, empresa)
    devolucoes = _filtrar_por_empresa(devolucoes, empresa)

    return {
        "material": material,
        "levantamentos": levantamentos,
        "devolucoes": devolucoes,
    }



def obter_levantamentos_empregado(empregado):
    return (
        _obter_queryset_base_levantamentos()
        .filter(
            empregado=empregado,
            empresa_id=empregado.empresa_id,
            material__empresa_id=empregado.empresa_id,
        )
        .order_by("-data", "-criado_em")
    )



def obter_devolucoes_empregado(empregado):
    return (
        _obter_queryset_base_devolucoes()
        .filter(
            empregado=empregado,
            empresa_id=empregado.empresa_id,
            material__empresa_id=empregado.empresa_id,
        )
        .order_by("-data", "-criado_em")
    )



def obter_levantamentos_admin(empresa=None):
    queryset = _obter_queryset_base_levantamentos().order_by("-data", "-criado_em")
    return _filtrar_movimentos_material_por_empresa(queryset, empresa)


def obter_contexto_filtros_levantamentos_admin(empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    return {
        "empregados": Empregados.objects.filter(empresa_id=empresa_id).order_by("nome"),
        "materiais": Material.objects.filter(empresa_id=empresa_id).order_by("nome"),
        "projetos": Projeto.objects.filter(empresa_id=empresa_id).order_by("nome"),
    }


def obter_levantamentos_admin_filtrados(*, empresa=None, filtros=None):
    filtros = filtros or {}
    queryset = obter_levantamentos_admin(empresa=empresa)

    empregado_id = (filtros.get("empregado") or "").strip()
    material_id = (filtros.get("material") or "").strip()
    projeto_id = (filtros.get("projeto") or "").strip()
    data_inicio = (filtros.get("data_inicio") or "").strip()
    data_fim = (filtros.get("data_fim") or "").strip()

    if empregado_id:
        queryset = queryset.filter(empregado_id=empregado_id)
    if material_id:
        queryset = queryset.filter(material_id=material_id)
    if projeto_id:
        queryset = queryset.filter(projeto_id=projeto_id)

    if data_inicio:
        data_inicio_parsed = parse_date(data_inicio)
        if data_inicio_parsed:
            queryset = queryset.filter(data__gte=data_inicio_parsed)

    if data_fim:
        data_fim_parsed = parse_date(data_fim)
        if data_fim_parsed:
            queryset = queryset.filter(data__lte=data_fim_parsed)

    return {
        "levantamentos": queryset,
        "filtros": {
            "empregado": empregado_id,
            "material": material_id,
            "projeto": projeto_id,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
    }



def obter_devolucoes_admin(empresa=None):
    queryset = _obter_queryset_base_devolucoes().order_by("-data", "-criado_em")
    return _filtrar_movimentos_material_por_empresa(queryset, empresa)
