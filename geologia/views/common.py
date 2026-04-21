from django.contrib import messages
from django.shortcuts import redirect

from plataforma.models import PerfilPlataforma


ADMIN_TIPOS_ACESSO_PLATAFORMA = ["platform_owner", "platform_admin"]
ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]
ADMIN_TIPOS_ACESSO_GEOLOGIA = ADMIN_TIPOS_ACESSO_PLATAFORMA + ADMIN_TIPOS_ACESSO_EMPRESA


def obter_contexto_admin_geologia(request):
    if request.user.is_superuser:
        return {
            "perfil": None,
            "empresa": None,
            "empresa_id": None,
            "is_global": True,
        }

    perfil = (
        PerfilPlataforma.objects.filter(
            user=request.user,
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


def obter_empresa_admin_geologia(request):
    contexto_admin = obter_contexto_admin_geologia(request)
    if not contexto_admin:
        messages.error(request, "Nao tens permissao para aceder a area de geologia.")
        return None, redirect("projetos:redirect_after_login")

    empresa = contexto_admin.get("empresa")
    empresa_id = contexto_admin.get("empresa_id")

    if contexto_admin.get("is_global"):
        return None, contexto_admin, None

    if not empresa or not empresa_id:
        messages.error(request, "O utilizador administrador nao esta associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, contexto_admin, None


def filtrar_queryset_por_empresa(queryset, empresa=None):
    if empresa is None:
        return queryset
    return queryset.filter(empresa=empresa)
