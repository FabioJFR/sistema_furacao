from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from plataforma.models import PerfilPlataforma
from projetos.models import Empregados


ADMIN_TIPOS_ACESSO_PLATAFORMA = ["platform_owner", "platform_admin"]
ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]
TIPOS_ACESSO_AREA_EMPREGADO = ["empregado", "individual"]


def _obter_perfil_plataforma(user):
    if not user.is_authenticated:
        return None

    return PerfilPlataforma.objects.filter(
        user=user,
        ativo=True,
    ).first()


def _obter_empregado(user):
    if not user.is_authenticated:
        return None

    return Empregados.objects.filter(user=user).first()


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


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if user_is_global_admin(request.user):
            return view_func(request, *args, **kwargs)

        if user_is_empresa_admin(request.user):
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