from django.shortcuts import get_object_or_404
from projetos.models import Medicao


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def _filtrar_por_empresa(qs, empresa=None):
    if not empresa:
        return qs

    empresa_id = _resolver_empresa_id(empresa)
    return qs.filter(
        empresa_id=empresa_id,
        furo__empresa_id=empresa_id,
    )


def obter_lista_medicoes(empresa=None):
    qs = Medicao.objects.select_related("furo")
    qs = _filtrar_por_empresa(qs, empresa)

    return qs.order_by("-criado_em", "-profundidade_medida")


def obter_medicao(pk, empresa=None):
    qs = Medicao.objects.select_related("furo")
    qs = _filtrar_por_empresa(qs, empresa)

    return get_object_or_404(qs, pk=pk)