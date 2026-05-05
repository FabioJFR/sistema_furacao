from django.shortcuts import get_object_or_404
from django.db.models import Count

from projetos.models import PlaneamentoTurno


def listar_planeamentos_empresa(empresa, *, filtros=None):
    filtros = filtros or {}
    qs = PlaneamentoTurno.objects.filter(empresa=empresa).select_related("projeto", "furo", "empregado", "maquina")

    estado = (filtros.get("estado") or "").strip()
    turno = (filtros.get("turno") or "").strip()
    data_inicio = (filtros.get("data_inicio") or "").strip()
    data_fim = (filtros.get("data_fim") or "").strip()

    if estado:
        qs = qs.filter(estado=estado)
    if turno:
        qs = qs.filter(turno=turno)
    if data_inicio:
        qs = qs.filter(data_inicio__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data_inicio__lte=data_fim)

    return qs.order_by("-data_inicio", "turno")


def resumir_capacidade_por_turno(*, queryset):
    return (
        queryset.values("turno", "estado")
        .annotate(total=Count("id"))
        .order_by("turno", "estado")
    )


def obter_planeamento_empresa(*, pk, empresa):
    return get_object_or_404(
        PlaneamentoTurno.objects.select_related("projeto", "furo", "empregado", "maquina"),
        pk=pk,
        empresa=empresa,
    )
