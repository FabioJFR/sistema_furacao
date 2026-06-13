from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from plataforma.decorators import platform_admin_required
from plataforma.selectors.riscos_deploy import (
    listar_checklist_pos_deploy,
    listar_checklist_pre_deploy,
    listar_comandos_deploy_operacional,
    listar_resumo_riscos_deploy,
    listar_riscos_deploy,
    listar_smoke_test_piloto_mvp,
    listar_tickets_friccoes_piloto_mvp,
)


@login_required
@platform_admin_required
def riscos_deploy_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, "Esta área está reservada ao superutilizador.")
        return redirect("plataforma:dashboard")

    context = {
        "riscos": listar_riscos_deploy(),
        "resumo": listar_resumo_riscos_deploy(),
        "checklist_pre_deploy": listar_checklist_pre_deploy(),
        "checklist_pos_deploy": listar_checklist_pos_deploy(),
        "comandos_deploy_operacional": listar_comandos_deploy_operacional(),
        "smoke_test_piloto_mvp": listar_smoke_test_piloto_mvp(),
        "tickets_friccoes_piloto_mvp": listar_tickets_friccoes_piloto_mvp(),
    }
    return render(request, "plataforma/riscos_deploy.html", context)
