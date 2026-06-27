from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from plataforma.decorators import platform_admin_required
from plataforma.selectors.dashboard import (
    enriquecer_empresas_dashboard,
    listar_ultimos_logins,
    listar_utilizadores_online,
    obter_alertas_renovacao_qs,
    obter_empresas_dashboard_qs,
    obter_metricas_comerciais_dashboard,
    obter_metricas_contas_dashboard,
    obter_metricas_empresas_dashboard,
)
from projetos.selectors.dashboard import (
    obter_checklist_piloto_operacional,
    obter_roteiro_piloto_operacional,
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
    metricas_contas = obter_metricas_contas_dashboard()
    metricas_comerciais = obter_metricas_comerciais_dashboard(empresas_qs)
    empresas_recentes = enriquecer_empresas_dashboard(list(empresas_qs[:12]))
    alertas_renovacao = obter_alertas_renovacao_qs()
    utilizadores_online = listar_utilizadores_online()
    ultimos_logins = listar_ultimos_logins()
    empresa_piloto = empresas_qs.first() if request.user.is_superuser else None

    context = {
        "perfil": perfil,
        **metricas,
        **metricas_contas,
        **metricas_comerciais,
        "empresas": empresas_recentes,
        "alertas_renovacao": alertas_renovacao,
        "utilizadores_online": utilizadores_online,
        "ultimos_logins": ultimos_logins,
    }
    if request.user.is_superuser:
        context.update(
            {
                "mvp_empresa_piloto": empresa_piloto,
                "mvp_piloto": obter_checklist_piloto_operacional(empresa=empresa_piloto),
                "mvp_roteiro_piloto": obter_roteiro_piloto_operacional(),
            }
        )

    return render(request, "plataforma/dashboard.html", context)
