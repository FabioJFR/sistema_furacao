from django.contrib import messages
from django.shortcuts import redirect

from core.permissions import user_is_global_admin
from projetos.selectors.dashboard import resolver_empresa_contexto_global_dashboard
from projetos.selectors.acesso import (
    obter_contexto_admin_projetos,
    obter_empregado_por_user,
    resolver_empregado_por_user_ou_email,
)


def obter_empresa_admin_contexto(
    *,
    request,
    mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
    mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
    redirect_sem_permissao="projetos:redirect_after_login",
    redirect_sem_empresa="projetos:dashboard",
):
    if user_is_global_admin(request.user):
        empresa_id = request.GET.get("empresa") or request.GET.get("empresa_contexto")
        empresa, _ = resolver_empresa_contexto_global_dashboard(empresa_id=empresa_id)
        if not empresa:
            messages.error(request, "Não existem empresas disponíveis para esta área.")
            return None, redirect(redirect_sem_permissao)
        return empresa, None

    contexto_admin = obter_contexto_admin_projetos(request.user)
    if not contexto_admin:
        messages.error(request, mensagem_sem_permissao)
        return None, redirect(redirect_sem_permissao)

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)
    if not empresa_id or not empresa:
        messages.error(request, mensagem_sem_empresa)
        return None, redirect(redirect_sem_empresa)

    return empresa, None


def obter_empregado_autenticado_contexto(
    *,
    request,
    mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
    mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
    redirect_sem_empregado="projetos:redirect_after_login",
    redirect_sem_empresa="projetos:redirect_after_login",
    vincular_por_email=True,
):
    if vincular_por_email:
        empregado, ligado_por_fallback = resolver_empregado_por_user_ou_email(request.user)
    else:
        empregado = obter_empregado_por_user(request.user)
        ligado_por_fallback = False

    if not empregado:
        messages.error(request, mensagem_sem_empregado)
        return None, False, redirect(redirect_sem_empregado)

    if not empregado.empresa_id:
        messages.error(request, mensagem_sem_empresa)
        return None, ligado_por_fallback, redirect(redirect_sem_empresa)

    return empregado, ligado_por_fallback, None
