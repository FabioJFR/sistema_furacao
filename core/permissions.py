from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from projetos.selectors.acesso import (
    obter_empregado_por_user,
    obter_perfil_ativo_por_user,
)


ADMIN_TIPOS_ACESSO_PLATAFORMA = ["platform_owner", "platform_admin"]
ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]
TIPOS_ACESSO_AREA_EMPREGADO = ["empregado", "individual"]
FUNCAO_GEOLOGO = "geologo"
FUNCAO_ENCARREGADO_OBRA = "encarregado_obra"
ROTAS_3D_GEOLOGO_PERMITIDAS = {
    "projetos:modelos_3d_hub",
    "projetos:modelo_3d_wireframe",
    "projetos:modelo_3d_block_model",
    "projetos:modelo_3d_implicit",
    "projetos:modelo_3d_wireframe_conteudo",
    "projetos:modelo_3d_wireframe_download",
    "projetos:modelo_3d_wireframe_apagar",
    "projetos:modelo_3d_block_conteudo",
    "projetos:modelo_3d_block_config",
    "projetos:modelo_3d_block_download",
    "projetos:modelo_3d_block_apagar",
    "projetos:modelo_3d_implicit_conteudo",
    "projetos:modelo_3d_implicit_config",
    "projetos:modelo_3d_implicit_download",
    "projetos:modelo_3d_implicit_apagar",
    "projetos:block_model_list",
    "projetos:block_model_create",
    "projetos:block_model_delete",
    "projetos:block_model_detail",
    "projetos:block_model_3d",
    "projetos:block_model_export_json",
    "projetos:block_model_export_csv",
    "projetos:block_model_regenerate_cells",
}


def _obter_perfil_plataforma(user):
    return obter_perfil_ativo_por_user(user)


def _obter_empregado(user):
    if not user.is_authenticated:
        return None
    return obter_empregado_por_user(user)


def user_is_global_admin(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    perfil = _obter_perfil_plataforma(user)
    if not perfil:
        return False

    return perfil.tipo_acesso in ADMIN_TIPOS_ACESSO_PLATAFORMA


def user_is_platform_admin(user):
    return user_is_global_admin(user)


def user_is_empresa_admin(user):
    if not user.is_authenticated:
        return False

    if user_is_global_admin(user):
        return True

    perfil = _obter_perfil_plataforma(user)
    if not perfil:
        return False

    return perfil.tipo_acesso in ADMIN_TIPOS_ACESSO_EMPRESA


def user_is_empregado(user):
    if not user.is_authenticated:
        return False

    if user_is_global_admin(user):
        return False

    perfil = _obter_perfil_plataforma(user)

    if perfil:
        if perfil.tipo_acesso in ADMIN_TIPOS_ACESSO_PLATAFORMA + ADMIN_TIPOS_ACESSO_EMPRESA:
            return False

        if perfil.tipo_acesso in TIPOS_ACESSO_AREA_EMPREGADO:
            return True

    empregado = _obter_empregado(user)
    if not empregado:
        return False

    return bool(empregado.aprovado and empregado.empresa_id)


def user_can_access_area_empregado(user):
    if not user.is_authenticated:
        return False

    if user_is_global_admin(user):
        return True

    perfil = _obter_perfil_plataforma(user)
    if perfil and perfil.tipo_acesso in ADMIN_TIPOS_ACESSO_EMPRESA + TIPOS_ACESSO_AREA_EMPREGADO:
        return True

    empregado = _obter_empregado(user)
    if not empregado:
        return False

    return bool(empregado.aprovado and empregado.empresa_id)


def _user_tem_funcao_empregado(user, funcao):
    if not user_is_empregado(user):
        return False
    empregado = _obter_empregado(user)
    if not empregado:
        return False
    return (empregado.funcao or "").strip().lower() == funcao


def user_is_geologo(user):
    return _user_tem_funcao_empregado(user, FUNCAO_GEOLOGO)


def user_is_encarregado_obra(user):
    return _user_tem_funcao_empregado(user, FUNCAO_ENCARREGADO_OBRA)


def user_can_access_geologia_operacional(user):
    if not user.is_authenticated:
        return False
    if user_is_global_admin(user) or user_is_empresa_admin(user):
        return True
    return user_is_geologo(user) or user_is_encarregado_obra(user)


def user_can_access_3d_geologo(user, rota_nome=None):
    if not user.is_authenticated:
        return False
    if user_is_global_admin(user) or user_is_empresa_admin(user):
        return True
    if not user_is_geologo(user):
        return False
    return bool(rota_nome and rota_nome in ROTAS_3D_GEOLOGO_PERMITIDAS)


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if user_is_global_admin(request.user):
            return view_func(request, *args, **kwargs)

        if user_is_empresa_admin(request.user):
            return view_func(request, *args, **kwargs)

        rota_nome = getattr(getattr(request, "resolver_match", None), "view_name", None)
        if user_can_access_3d_geologo(request.user, rota_nome):
            return view_func(request, *args, **kwargs)

        messages.error(request, "Não tens permissão para aceder a esta área.")
        return redirect("projetos:redirect_after_login")

    return wrapper


def empresa_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if user_is_global_admin(request.user):
            return view_func(request, *args, **kwargs)

        perfil = _obter_perfil_plataforma(request.user)
        if perfil and perfil.tipo_acesso in ADMIN_TIPOS_ACESSO_EMPRESA:
            return view_func(request, *args, **kwargs)

        messages.error(request, "Não tens permissão para aceder a esta área.")
        return redirect("projetos:redirect_after_login")

    return wrapper


def empregado_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if user_can_access_area_empregado(request.user):
            return view_func(request, *args, **kwargs)

        messages.error(
            request,
            "A tua conta não tem permissão para aceder a esta área.",
        )
        return redirect("projetos:redirect_after_login")

    return wrapper


def geologo_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if user_is_geologo(request.user):
            return view_func(request, *args, **kwargs)

        messages.error(
            request,
            "A tua conta não tem permissão para aceder ao dashboard de geologia.",
        )
        return redirect("projetos:redirect_after_login")

    return wrapper


def encarregado_obra_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if user_is_encarregado_obra(request.user):
            return view_func(request, *args, **kwargs)

        messages.error(
            request,
            "A tua conta não tem permissão para aceder ao dashboard de encarregado de obra.",
        )
        return redirect("projetos:redirect_after_login")

    return wrapper


def geologia_operacional_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if user_can_access_geologia_operacional(request.user):
            return view_func(request, *args, **kwargs)

        messages.error(
            request,
            "A tua conta não tem permissão para aceder à área operacional de geologia.",
        )
        return redirect("projetos:redirect_after_login")

    return wrapper
