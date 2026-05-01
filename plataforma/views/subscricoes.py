

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from plataforma.decorators import platform_admin_required
from plataforma.services.subscricoes import construir_contexto_subscricao_list


# TODO futuro:
# - mover regras de filtros/ordenação para selectors próprios
# - criar detalhe da subscrição
# - permitir renovar/cancelar/reactivar subscrição
# - destacar subscrições expiradas e próximas do vencimento
# - ligar subscrições a pagamentos reais


@login_required
@platform_admin_required
def subscricao_list(request):
    return render(
        request,
        "plataforma/subscricao_list.html",
        construir_contexto_subscricao_list(perfil=request.perfil_plataforma),
    )
