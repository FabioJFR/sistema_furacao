import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.permissions import admin_required
from projetos.services.dashboard_contexto import (
    montar_contexto_dashboard,
    obter_contexto_admin_dashboard,
)

logger = logging.getLogger("core")


@login_required
@admin_required
def graficos_dashboard(request):
    logger.info(
        "Entrada na view graficos_dashboard (compat). user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    contexto_admin = obter_contexto_admin_dashboard(request)
    if contexto_admin is None:
        logger.warning(
            "Redirecionamento em graficos_dashboard (compat) por falta de contexto administrativo. user_id=%s",
            request.user.id,
        )
        return redirect("projetos:redirect_after_login")

    context = montar_contexto_dashboard(
        request=request,
        contexto_admin=contexto_admin,
        incluir_mapa=False,
    )

    if not context.get("empresa_dashboard"):
        return redirect("projetos:redirect_after_login")

    return render(request, "projetos/graficos_dashboard.html", context)
