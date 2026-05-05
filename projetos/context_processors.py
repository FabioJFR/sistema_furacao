from core.permissions import user_is_empresa_admin, user_is_empregado, user_is_platform_admin
from projetos.models import MaquinaAvaria
from projetos.selectors.acesso import obter_empregado_por_user, obter_perfil_ativo_por_user
from projetos.selectors.preferencias import obter_ou_criar_preferencias_user


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
            "empregado_menu_funcao": "",
            "tamanho_texto": "normal",
            "empresa_menu_logo_url": "",
        }

    perfil = obter_perfil_ativo_por_user(user)

    perfil_ativo = perfil is not None

    is_platform_owner = perfil_ativo and perfil.tipo_acesso == "platform_owner"
    is_platform_admin = user_is_platform_admin(user)
    is_empresa_admin = user_is_empresa_admin(user) and not is_platform_admin

    empregado_menu_obj = obter_empregado_por_user(user)

    is_admin_user = is_empresa_admin
    is_empregado_user = user_is_empregado(user)
    total_avarias_maquinas_abertas_menu = 0
    total_minhas_avarias_maquinas_abertas_menu = 0

    empresa_id_menu = getattr(perfil, "empresa_id", None) or getattr(empregado_menu_obj, "empresa_id", None)
    if is_admin_user and empresa_id_menu:
        total_avarias_maquinas_abertas_menu = MaquinaAvaria.objects.filter(
            empresa_id=empresa_id_menu,
            status__in=["aberta", "em_reparacao"],
        ).count()
    if is_empregado_user and empregado_menu_obj and empregado_menu_obj.empresa_id:
        total_minhas_avarias_maquinas_abertas_menu = MaquinaAvaria.objects.filter(
            empresa_id=empregado_menu_obj.empresa_id,
            responsavel_empregado_id=empregado_menu_obj.id,
            status__in=["aberta", "em_reparacao"],
        ).count()

    preferencias = getattr(request, "sf_preferencias", None)
    if preferencias is None:
        preferencias, _ = obter_ou_criar_preferencias_user(user)

    empresa_menu = getattr(perfil, "empresa", None) or getattr(empregado_menu_obj, "empresa", None)
    empresa_menu_logo_url = ""
    if empresa_menu and getattr(empresa_menu, "logo", None):
        try:
            empresa_menu_logo_url = empresa_menu.logo.url
        except Exception:
            empresa_menu_logo_url = ""

    return {
        "is_admin_user": is_admin_user,
        "is_empregado_user": is_empregado_user,
        "is_platform_admin": is_platform_admin,
        "is_platform_owner": is_platform_owner,
        "is_empresa_admin": is_empresa_admin,
        "perfil_plataforma": perfil,
        "empregado_menu_obj": empregado_menu_obj,
        "empregado_menu_funcao": (getattr(empregado_menu_obj, "funcao", "") or "").strip().lower(),
        "total_avarias_maquinas_abertas_menu": total_avarias_maquinas_abertas_menu,
        "total_minhas_avarias_maquinas_abertas_menu": total_minhas_avarias_maquinas_abertas_menu,
        "tamanho_texto": getattr(preferencias, "tamanho_texto", "normal"),
        "empresa_menu_logo_url": empresa_menu_logo_url,
    }
