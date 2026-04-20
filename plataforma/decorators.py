from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from plataforma.models import PerfilPlataforma


# TODO futuro:
# - mover esta lógica para um módulo mais completo de permissions/access
# - suportar auditoria de acessos negados
# - permitir regras mais finas por feature/plano/subscrição


def obter_perfil_plataforma(user):
    if not user.is_authenticated:
        return None

    perfil = PerfilPlataforma.objects.filter(user=user, ativo=True).first()
    return perfil


def user_is_platform_admin(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    perfil = obter_perfil_plataforma(user)
    if not perfil:
        return False

    return perfil.tipo_acesso in ["platform_owner", "platform_admin"]


# TODO futuro:
# - criar versão com parâmetros para aceitar múltiplos tipos de acesso
# - reutilizar em todas as views da app plataforma

def platform_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if request.user.is_superuser:
            request.perfil_plataforma = None
            return view_func(request, *args, **kwargs)

        perfil = obter_perfil_plataforma(request.user)

        if not perfil or perfil.tipo_acesso not in ["platform_owner", "platform_admin"]:
            messages.error(request, "Não tens permissão para aceder a esta área da plataforma.")
            return redirect("projetos:redirect_after_login")

        request.perfil_plataforma = perfil
        return view_func(request, *args, **kwargs)

    return _wrapped_view


# TODO futuro:
# - usar este decorator nas áreas mais críticas da plataforma
# - reservar ações sensíveis apenas ao dono da plataforma

def platform_owner_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if request.user.is_superuser:
            request.perfil_plataforma = None
            return view_func(request, *args, **kwargs)

        perfil = obter_perfil_plataforma(request.user)

        if not perfil or perfil.tipo_acesso != "platform_owner":
            messages.error(request, "Esta ação está reservada ao dono da plataforma.")
            return redirect("projetos:redirect_after_login")

        request.perfil_plataforma = perfil
        return view_func(request, *args, **kwargs)

    return _wrapped_view
