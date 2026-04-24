from core.permissions import user_is_empresa_admin, user_is_empregado, user_is_platform_admin
from projetos.selectors.acesso import obter_empregado_por_user, obter_perfil_ativo_por_user


def menu_context(request):
    user = request.user

    if not user.is_authenticated:
        return {
            "is_admin_user": False,
            "is_empregado_user": False,
            "is_platform_admin": False,
            "is_empresa_admin": False,
            "is_platform_owner": False,
            "perfil_plataforma": None,
            "empregado_menu_obj": None,
        }

    perfil = obter_perfil_ativo_por_user(user)

    perfil_ativo = perfil is not None

    is_platform_owner = perfil_ativo and perfil.tipo_acesso == "platform_owner"
    is_platform_admin = user_is_platform_admin(user)
    is_empresa_admin = user_is_empresa_admin(user) and not is_platform_admin

    empregado_menu_obj = obter_empregado_por_user(user)

    is_admin_user = is_empresa_admin
    is_empregado_user = user_is_empregado(user)

    return {
        "is_admin_user": is_admin_user,
        "is_empregado_user": is_empregado_user,
        "is_platform_admin": is_platform_admin,
        "is_platform_owner": is_platform_owner,
        "is_empresa_admin": is_empresa_admin,
        "perfil_plataforma": perfil,
        "empregado_menu_obj": empregado_menu_obj,
    }
