from django.shortcuts import get_object_or_404

from projetos.models import Maquina


def obter_lista_maquinas():
    return Maquina.objects.select_related("projeto_atual").prefetch_related("projetos", "furos").order_by("nome")


def obter_maquina(maquina_id):
    return get_object_or_404(
        Maquina.objects.select_related("projeto_atual").prefetch_related("projetos", "furos"),
        pk=maquina_id
    )


def obter_contexto_maquina_detail(maquina_id):
    maquina = obter_maquina(maquina_id)

    return {
        "maquina": maquina,
        "projetos": maquina.projetos.all(),
        "furos": maquina.furos.all(),
    }