from django.shortcuts import get_object_or_404

from projetos.models import DevolucaoMaterial, LevantamentoMaterial, Material



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



def obter_material(material_id, empresa=None):
    queryset = _obter_queryset_base_materiais()
    queryset = _filtrar_por_empresa(queryset, empresa)
    return get_object_or_404(queryset, pk=material_id)



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



def obter_devolucoes_admin(empresa=None):
    queryset = _obter_queryset_base_devolucoes().order_by("-data", "-criado_em")
    return _filtrar_movimentos_material_por_empresa(queryset, empresa)