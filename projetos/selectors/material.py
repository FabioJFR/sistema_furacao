
from django.shortcuts import get_object_or_404

from projetos.models import (
    Material,
    LevantamentoMaterial,
    DevolucaoMaterial,
)


def obter_lista_materiais():
    return Material.objects.select_related("projeto", "furo").order_by("nome")


def obter_material(material_id):
    return get_object_or_404(
        Material.objects.select_related("projeto", "furo"),
        pk=material_id
    )


def obter_contexto_material_detail(material_id):
    material = obter_material(material_id)

    levantamentos = material.levantamentos.select_related(
        "empregado", "projeto", "furo"
    ).all()

    devolucoes = material.devolucoes.select_related(
        "empregado", "projeto", "furo"
    ).all()

    return {
        "material": material,
        "levantamentos": levantamentos,
        "devolucoes": devolucoes,
    }


def obter_levantamentos_empregado(empregado):
    return LevantamentoMaterial.objects.filter(
        empregado=empregado
    ).select_related("material", "projeto", "furo").order_by("-data", "-criado_em")


def obter_devolucoes_empregado(empregado):
    return DevolucaoMaterial.objects.filter(
        empregado=empregado
    ).select_related("material", "projeto", "furo").order_by("-data", "-criado_em")


def obter_levantamentos_admin():
    return LevantamentoMaterial.objects.select_related(
        "empregado", "material", "projeto", "furo"
    ).order_by("-data", "-criado_em")


def obter_devolucoes_admin():
    return DevolucaoMaterial.objects.select_related(
        "empregado", "material", "projeto", "furo"
    ).order_by("-data", "-criado_em")