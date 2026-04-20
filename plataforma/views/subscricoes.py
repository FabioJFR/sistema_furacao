

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from plataforma.decorators import platform_admin_required
from plataforma.models import SubscricaoEmpresa


# TODO futuro:
# - mover regras de filtros/ordenação para selectors próprios
# - criar detalhe da subscrição
# - permitir renovar/cancelar/reactivar subscrição
# - destacar subscrições expiradas e próximas do vencimento
# - ligar subscrições a pagamentos reais


@login_required
@platform_admin_required
def subscricao_list(request):
    subscricoes = (
        SubscricaoEmpresa.objects
        .select_related("empresa", "plano")
        .order_by("estado", "-data_inicio", "-criado_em")
    )

    # TODO futuro:
    # - adicionar filtros por estado, plano e intervalo de datas
    # - adicionar pesquisa por empresa
    total_subscricoes = subscricoes.count()
    subscricoes_ativas = subscricoes.filter(estado="ativa").count()
    subscricoes_pendentes = subscricoes.filter(estado="pendente").count()
    subscricoes_expiradas = subscricoes.filter(estado="expirada").count()
    subscricoes_canceladas = subscricoes.filter(estado="cancelada").count()

    context = {
        "perfil": request.perfil_plataforma,
        "subscricoes": subscricoes,
        "total_subscricoes": total_subscricoes,
        "subscricoes_ativas": subscricoes_ativas,
        "subscricoes_pendentes": subscricoes_pendentes,
        "subscricoes_expiradas": subscricoes_expiradas,
        "subscricoes_canceladas": subscricoes_canceladas,
    }

    return render(request, "plataforma/subscricao_list.html", context)