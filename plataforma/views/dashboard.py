from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from plataforma.decorators import platform_admin_required
from plataforma.selectors.dashboard import (
    obter_alertas_renovacao_qs,
    obter_empresas_dashboard_qs,
    obter_metricas_empresas_dashboard,
)

# TODO futuro:
# - substituir este padrão por selector/service dedicado para dashboard da plataforma
# - quando Empresa.plano passar para ForeignKey real, rever queries e métricas


@login_required
@platform_admin_required
def dashboard_plataforma(request):
    perfil = request.perfil_plataforma

    empresas_qs = obter_empresas_dashboard_qs()
    metricas = obter_metricas_empresas_dashboard(empresas_qs)
    alertas_renovacao = obter_alertas_renovacao_qs()

    context = {
        "perfil": perfil,
        **metricas,
        "empresas": empresas_qs[:12],
        "alertas_renovacao": alertas_renovacao,
    }

    return render(request, "plataforma/dashboard.html", context)
