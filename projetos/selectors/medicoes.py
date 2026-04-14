from django.shortcuts import get_object_or_404

from projetos.models import Medicao


def obter_lista_medicoes():
    return (
        Medicao.objects
        .select_related("furo")
        .order_by("-criado_em", "-profundidade_medida")
    )


def obter_medicao(pk):
    return get_object_or_404(
        Medicao.objects.select_related("furo"),
        pk=pk
    )