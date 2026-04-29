from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404

from plataforma.models import FuroArquivadoPlataforma


def listar_furos_arquivados_com_filtros(
    *,
    empresa_id=None,
    nome_furo="",
    estado="",
    page=1,
    per_page=20,
):
    qs = (
        FuroArquivadoPlataforma.objects.select_related("empresa", "terminado_por")
        .order_by("-criado_em")
    )

    if empresa_id:
        qs = qs.filter(empresa_id=empresa_id)

    if nome_furo:
        qs = qs.filter(nome_furo__icontains=nome_furo.strip())

    if estado:
        qs = qs.filter(estado_no_arquivo=estado.strip())

    paginator = Paginator(qs, per_page)
    return paginator.get_page(page)


def listar_estados_arquivo_furos():
    return [
        item
        for item in (
            FuroArquivadoPlataforma.objects.values_list("estado_no_arquivo", flat=True)
            .distinct()
            .order_by("estado_no_arquivo")
        )
        if item
    ]


def obter_furo_arquivado(pk):
    return get_object_or_404(
        FuroArquivadoPlataforma.objects.select_related("empresa", "terminado_por"),
        pk=pk,
    )
