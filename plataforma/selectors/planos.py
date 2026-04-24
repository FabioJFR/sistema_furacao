from django.shortcuts import get_object_or_404

from plataforma.models import Plano


def listar_planos_dashboard():
    return Plano.objects.all().order_by("preco_mensal")


def obter_plano_por_pk(pk):
    return get_object_or_404(Plano, pk=pk)


def listar_planos_ativos():
    return Plano.objects.filter(ativo=True).order_by("preco_mensal")


def listar_planos_para_admin():
    return Plano.objects.filter(ativo=True).order_by("tipo", "preco_mensal", "nome")


def obter_plano_ativo(pk):
    return get_object_or_404(Plano, pk=pk, ativo=True)


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
