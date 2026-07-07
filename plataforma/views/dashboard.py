from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from plataforma.decorators import platform_admin_required
from plataforma.services.dashboard import construir_contexto_dashboard_plataforma


@login_required
@platform_admin_required
def dashboard_plataforma(request):
    context = construir_contexto_dashboard_plataforma(
        perfil=request.perfil_plataforma,
        user=request.user,
    )
    return render(request, "plataforma/dashboard.html", context)
