from plataforma.models import Empresa, PerfilPlataforma


ADMIN_TIPOS_ACESSO_PLATAFORMA = ["platform_owner", "platform_admin"]
ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]
ADMIN_TIPOS_ACESSO_GEOLOGIA = ADMIN_TIPOS_ACESSO_PLATAFORMA + ADMIN_TIPOS_ACESSO_EMPRESA


def obter_contexto_admin_geologia_user(user):
    if user.is_superuser:
        return {
            "perfil": None,
            "empresa": None,
            "empresa_id": None,
            "is_global": True,
        }

    perfil = (
        PerfilPlataforma.objects.filter(
            user=user,
            ativo=True,
            tipo_acesso__in=ADMIN_TIPOS_ACESSO_GEOLOGIA,
        )
        .select_related("empresa")
        .first()
    )
    if not perfil:
        return None

    is_global = perfil.tipo_acesso in ADMIN_TIPOS_ACESSO_PLATAFORMA
    return {
        "perfil": perfil,
        "empresa": getattr(perfil, "empresa", None),
        "empresa_id": getattr(perfil, "empresa_id", None),
        "is_global": is_global,
    }


def obter_empresas_ativas_geologia():
    return Empresa.objects.filter(ativo=True).order_by("nome")


def resolver_empresa_global_geologia(empresa_param):
    empresas_disponiveis = obter_empresas_ativas_geologia()
    empresa_selecionada = None
    if empresa_param:
        empresa_selecionada = empresas_disponiveis.filter(pk=empresa_param).first()
    return empresa_selecionada, empresas_disponiveis
