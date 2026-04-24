from django.shortcuts import get_object_or_404

from geologia.models import LogGeologicoFuro
from projetos.models import Furo


def filtrar_queryset_por_empresa(queryset, empresa=None):
    if empresa is None:
        return queryset
    return queryset.filter(empresa=empresa)


def obter_furo_log_geologico(furo_id, empresa=None):
    queryset = filtrar_queryset_por_empresa(Furo.objects.select_related("projeto"), empresa=empresa)
    return get_object_or_404(queryset, pk=furo_id)


def obter_log_geologico(pk, empresa=None):
    logs_qs = filtrar_queryset_por_empresa(
        LogGeologicoFuro.objects.select_related("furo", "furo__projeto", "medicao", "missao_drone"),
        empresa=empresa,
    )
    return get_object_or_404(logs_qs, pk=pk)


def obter_anexos_log(log):
    return log.anexos.all().order_by("-criado_em")
