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


def construir_contexto_dashboard_plataforma(*, perfil, user):
    empresas_qs = obter_empresas_dashboard_qs()
    metricas = obter_metricas_empresas_dashboard(empresas_qs)
    metricas_contas = obter_metricas_contas_dashboard()
    metricas_comerciais = obter_metricas_comerciais_dashboard(empresas_qs)
    empresas_recentes = enriquecer_empresas_dashboard(list(empresas_qs[:12]))

    context = {
        "perfil": perfil,
        **metricas,
        **metricas_contas,
        **metricas_comerciais,
        "empresas": empresas_recentes,
        "alertas_renovacao": obter_alertas_renovacao_qs(),
        "utilizadores_online": listar_utilizadores_online(),
        "ultimos_logins": listar_ultimos_logins(),
    }

    if user.is_superuser:
        empresa_piloto = empresas_qs.first()
        context.update(
            {
                "mvp_empresa_piloto": empresa_piloto,
                "mvp_piloto": obter_checklist_piloto_operacional(empresa=empresa_piloto),
                "mvp_roteiro_piloto": obter_roteiro_piloto_operacional(),
            }
        )

    return context
