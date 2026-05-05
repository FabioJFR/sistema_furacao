from django.contrib import messages
from django.shortcuts import redirect

from core.permissions import user_is_empresa_admin, user_is_global_admin
from geologia.selectors.access import (
    obter_contexto_admin_geologia_user,
    resolver_empresa_global_geologia,
)
from projetos.selectors.acesso import obter_empregado_por_user


def obter_contexto_admin_geologia(request):
    return obter_contexto_admin_geologia_user(request.user)


def obter_empresa_admin_geologia(request):
    contexto_admin = obter_contexto_admin_geologia(request)
    if not contexto_admin:
        messages.error(request, "Nao tens permissao para aceder a area de geologia.")
        return None, redirect("projetos:redirect_after_login")

    empresa = contexto_admin.get("empresa")
    empresa_id = contexto_admin.get("empresa_id")

    if contexto_admin.get("is_global"):
        empresa_param = (request.GET.get("empresa") or request.POST.get("empresa") or "").strip()
        empresa_selecionada, empresas_disponiveis = resolver_empresa_global_geologia(empresa_param)
        if empresa_param and empresa_selecionada is None:
            messages.error(request, "A empresa selecionada para geologia nao existe ou nao esta disponivel.")
        contexto_admin["empresas_disponiveis"] = empresas_disponiveis
        contexto_admin["empresa_selecionada"] = empresa_selecionada
        contexto_admin["empresa_id"] = getattr(empresa_selecionada, "pk", None)
        contexto_admin["empresa"] = empresa_selecionada
        return empresa_selecionada, contexto_admin, None

    if not empresa or not empresa_id:
        messages.error(request, "O utilizador administrador nao esta associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, contexto_admin, None


def filtrar_queryset_por_empresa(queryset, empresa=None):
    if empresa is None:
        return queryset
    return queryset.filter(empresa=empresa)


def obter_empresa_geologia_operacional(request):
    if user_is_global_admin(request.user) or user_is_empresa_admin(request.user):
        empresa, contexto_admin, resposta_erro = obter_empresa_admin_geologia(request)
        if resposta_erro is None:
            return empresa, contexto_admin, None

    empregado = obter_empregado_por_user(request.user)
    if not empregado or not empregado.empresa_id:
        messages.error(request, "A tua conta não está associada a uma empresa para aceder à geologia.")
        return None, None, redirect("projetos:redirect_after_login")

    return empregado.empresa, {"is_empregado": True, "empresa": empregado.empresa}, None
