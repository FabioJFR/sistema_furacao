from django.shortcuts import get_object_or_404

from plataforma.models import Empresa, MovimentoFinanceiroPlataforma, SubscricaoEmpresa


def obter_empresa(pk):
    return get_object_or_404(Empresa, pk=pk)


def obter_empresa_com_plano(pk):
    return get_object_or_404(Empresa.objects.select_related("plano"), pk=pk)


def obter_subscricao_atual_empresa(empresa):
    return (
        SubscricaoEmpresa.objects
        .select_related("plano")
        .filter(empresa=empresa)
        .order_by("-data_inicio", "-criado_em")
        .first()
    )


def listar_movimentos_financeiros_empresa(empresa, limit=5):
    return (
        MovimentoFinanceiroPlataforma.objects
        .select_related("plano", "subscricao")
        .filter(empresa=empresa)
        .order_by("-data_vencimento", "-criado_em")[:limit]
    )
