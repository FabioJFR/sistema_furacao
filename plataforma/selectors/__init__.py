from core.domain import build_repositories
from django.shortcuts import get_object_or_404

from plataforma.domain_registry import PLATAFORMA_MODEL_MAP
from plataforma.models import Empresa, MovimentoFinanceiroPlataforma, Plano, SubscricaoEmpresa


PLATAFORMA_SELECTORS = build_repositories(PLATAFORMA_MODEL_MAP)


def listar_planos_ativos():
    return Plano.objects.filter(ativo=True).order_by("preco_mensal")


def listar_planos_para_admin():
    return Plano.objects.filter(ativo=True).order_by("tipo", "preco_mensal", "nome")


def construir_planos_periodos_precos(planos):
    planos_periodos = {
        str(plano.pk): plano.periodos_cobranca_disponiveis_normalizados
        for plano in planos
    }
    planos_precos = {
        str(plano.pk): {
            "preco_mensal": str(plano.preco_mensal or 0),
            "preco_anual": str(plano.preco_anual or 0),
        }
        for plano in planos
    }
    return planos_periodos, planos_precos


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
