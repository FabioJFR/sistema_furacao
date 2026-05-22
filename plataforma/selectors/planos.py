from django.shortcuts import get_object_or_404

from plataforma.models import Plano


def plano_e_trial(plano):
    if not plano:
        return False
    return float(plano.preco_mensal or 0) == 0 and float(plano.preco_anual or 0) == 0


def construir_contexto_trial_plano(plano):
    if not plano:
        return {
            "is_trial": False,
            "badge": "",
            "mensagem_curta": "",
            "mensagem_longa": "",
        }

    is_trial = plano_e_trial(plano)
    if is_trial:
        return {
            "is_trial": True,
            "badge": "Trial / prova",
            "mensagem_curta": "Plano sem cobrança, pensado para onboarding, validação de conta e arranque inicial.",
            "mensagem_longa": (
                "Este plano funciona como versão de prova: não gera cobrança inicial e é indicado "
                "para ativar a conta, validar o email do administrador e testar a operação antes "
                "de mudar para um plano comercial final."
            ),
        }

    return {
        "is_trial": False,
        "badge": "Plano comercial",
        "mensagem_curta": "Plano preparado para operação contínua com cobrança ativa.",
        "mensagem_longa": (
            "Este plano já representa a subscrição comercial da empresa. Use-o quando a conta "
            "estiver pronta para operação regular e ciclo de renovação normal."
        ),
    }


def enriquecer_planos_com_contexto_trial(planos):
    for plano in planos:
        plano.trial_contexto = construir_contexto_trial_plano(plano)
    return planos


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
            "is_trial": plano_e_trial(plano),
            "mensagem_trial": construir_contexto_trial_plano(plano)["mensagem_longa"],
        }
        for plano in planos
    }
    return planos_periodos, planos_precos
