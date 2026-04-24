

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from plataforma.decorators import platform_admin_required
from plataforma.selectors.subscricoes import listar_subscricoes, obter_metricas_subscricoes


# TODO futuro:
# - mover regras de filtros/ordenação para selectors próprios
# - criar detalhe da subscrição
# - permitir renovar/cancelar/reactivar subscrição
# - destacar subscrições expiradas e próximas do vencimento
# - ligar subscrições a pagamentos reais


@login_required
@platform_admin_required
def subscricao_list(request):
    subscricoes = listar_subscricoes()

    # TODO futuro:
    # - adicionar filtros por estado, plano e intervalo de datas
    # - adicionar pesquisa por empresa
    metricas = obter_metricas_subscricoes(subscricoes)

    context = {
        "perfil": request.perfil_plataforma,
        "subscricoes": subscricoes,
        **metricas,
    }

    return render(request, "plataforma/subscricao_list.html", context)
