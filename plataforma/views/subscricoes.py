

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from plataforma.decorators import platform_admin_required
from plataforma.selectors.subscricoes import (
    listar_subscricoes,
    mapear_pagamentos_pendentes_por_subscricao,
    obter_metricas_subscricoes,
)


# TODO futuro:
# - mover regras de filtros/ordenação para selectors próprios
# - criar detalhe da subscrição
# - permitir renovar/cancelar/reactivar subscrição
# - destacar subscrições expiradas e próximas do vencimento
# - ligar subscrições a pagamentos reais


@login_required
@platform_admin_required
def subscricao_list(request):
    subscricoes = list(listar_subscricoes())
    pagamentos_pendentes = mapear_pagamentos_pendentes_por_subscricao(subscricoes)
    for subscricao in subscricoes:
        subscricao.pagamento_pendente = pagamentos_pendentes.get(str(subscricao.pk))

    # TODO futuro:
    # - adicionar filtros por estado, plano e intervalo de datas
    # - adicionar pesquisa por empresa
    metricas = obter_metricas_subscricoes(listar_subscricoes())

    context = {
        "perfil": request.perfil_plataforma,
        "subscricoes": subscricoes,
        **metricas,
    }

    return render(request, "plataforma/subscricao_list.html", context)
