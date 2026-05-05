from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone

from projetos.models import ClienteContrato


def listar_clientes_contratos_empresa(empresa, *, filtros=None):
    filtros = filtros or {}
    status = (filtros.get("status") or "").strip()
    projeto_id = (filtros.get("projeto_id") or "").strip()
    termo = (filtros.get("termo") or "").strip()
    vencimento = (filtros.get("vencimento") or "").strip()

    qs = ClienteContrato.objects.filter(empresa=empresa).select_related("projeto").order_by("nome_cliente")

    if status:
        qs = qs.filter(status=status)
    if projeto_id:
        qs = qs.filter(projeto_id=projeto_id)
    if termo:
        qs = qs.filter(nome_cliente__icontains=termo)

    hoje = timezone.localdate()
    if vencimento == "vencido":
        qs = qs.filter(data_fim__isnull=False, data_fim__lt=hoje)
    elif vencimento == "7d":
        qs = qs.filter(data_fim__isnull=False, data_fim__gte=hoje, data_fim__lte=hoje + timedelta(days=7))
    elif vencimento == "30d":
        qs = qs.filter(data_fim__isnull=False, data_fim__gte=hoje, data_fim__lte=hoje + timedelta(days=30))

    return qs


def obter_cliente_contrato_empresa(*, pk, empresa):
    return get_object_or_404(
        ClienteContrato.objects.select_related("projeto", "empresa"),
        pk=pk,
        empresa=empresa,
    )
