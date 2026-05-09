from django.shortcuts import get_object_or_404

from projetos.models import ClienteContrato, ClienteContratoAdenda, ClienteContratoAnexo


def listar_clientes_contratos_empresa(empresa, *, filtros=None):
    filtros = filtros or {}
    status = (filtros.get("status") or "").strip()
    workflow = (filtros.get("workflow") or "").strip()
    projeto_id = (filtros.get("projeto_id") or "").strip()
    termo = (filtros.get("termo") or "").strip()
    qs = ClienteContrato.objects.filter(empresa=empresa).select_related("projeto").order_by("nome_cliente")

    if status:
        qs = qs.filter(status=status)
    if workflow:
        qs = qs.filter(workflow_comercial=workflow)
    if projeto_id:
        qs = qs.filter(projeto_id=projeto_id)
    if termo:
        qs = qs.filter(nome_cliente__icontains=termo)

    return qs


def obter_cliente_contrato_empresa(*, pk, empresa):
    return get_object_or_404(
        ClienteContrato.objects.select_related("projeto", "empresa").prefetch_related("anexos", "adendas", "historico_workflow__alterado_por"),
        pk=pk,
        empresa=empresa,
    )


def listar_anexos_cliente_contrato(*, cliente_contrato):
    return ClienteContratoAnexo.objects.filter(contrato=cliente_contrato).order_by("-criado_em")


def listar_adendas_cliente_contrato(*, cliente_contrato):
    return ClienteContratoAdenda.objects.filter(contrato=cliente_contrato).order_by("-data_adenda", "-criado_em")
