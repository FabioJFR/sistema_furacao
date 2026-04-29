from django.shortcuts import get_object_or_404

from projetos.models import Furo, Maquina, MaquinaAvaria


def listar_maquinas_empresa(empresa_id):
    return Maquina.objects.filter(empresa_id=empresa_id, ativo=True).order_by("nome")


def listar_furos_empresa(empresa_id):
    return Furo.objects.filter(empresa_id=empresa_id).order_by("nome")


def listar_avarias_empresa(empresa_id):
    return (
        MaquinaAvaria.objects.select_related("maquina", "projeto", "furo", "reportado_por")
        .filter(empresa_id=empresa_id)
        .order_by("-data_inicio", "-criado_em")
    )


def obter_avaria_empresa(pk, empresa_id):
    return get_object_or_404(
        MaquinaAvaria.objects.select_related("maquina", "projeto", "furo", "reportado_por"),
        pk=pk,
        empresa_id=empresa_id,
    )


def listar_avarias_responsavel(empregado_id, empresa_id):
    return (
        MaquinaAvaria.objects.select_related("maquina", "projeto", "furo", "reportado_por", "responsavel_empregado")
        .filter(
            empresa_id=empresa_id,
            responsavel_empregado_id=empregado_id,
        )
        .order_by("-data_inicio", "-criado_em")
    )


def obter_avaria_responsavel(pk, empregado_id, empresa_id):
    return get_object_or_404(
        MaquinaAvaria.objects.select_related("maquina", "projeto", "furo", "reportado_por", "responsavel_empregado"),
        pk=pk,
        empresa_id=empresa_id,
        responsavel_empregado_id=empregado_id,
    )
