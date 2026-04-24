import logging
from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.permissions import user_is_global_admin
from projetos.selectors.acesso import obter_contexto_admin_projetos
from projetos.selectors.dashboard import (
    obter_alertas_dashboard,
    obter_cards_dashboard,
    obter_empresa_dashboard_por_id,
    obter_empresas_contexto_dashboard,
    obter_graficos_dashboard,
    obter_intervalo_filtros,
    obter_opcoes_filtros_dashboard,
    resolver_empresa_contexto_global_dashboard,
)
from projetos.selectors.projetos import obter_projetos_mapa

logger = logging.getLogger("core")

def _resolver_empresa_contexto_global(request):
    empresa_id = request.GET.get("empresa") or request.GET.get("empresa_contexto")
    empresa, origem = resolver_empresa_contexto_global_dashboard(empresa_id=empresa_id)
    if empresa:
        if origem == "querystring":
            logger.info(
                "Contexto global do dashboard resolvido por querystring. user_id=%s, empresa_id=%s",
                request.user.id,
                empresa.id,
            )
        else:
            logger.info(
                "Contexto global do dashboard resolvido pela primeira empresa disponível. user_id=%s, empresa_id=%s",
                request.user.id,
                empresa.id,
            )
        return empresa

    if empresa_id:
        logger.warning(
            "Empresa pedida por utilizador global não encontrada. user_id=%s, empresa_id=%s",
            request.user.id,
            empresa_id,
        )

    logger.warning(
        "Não existem empresas disponíveis para contexto global do dashboard. user_id=%s",
        request.user.id,
    )
    return None


def _obter_contexto_admin_dashboard(request):
    logger.debug(
        "A verificar acesso ao dashboard: user_id=%s, username='%s'",
        getattr(request.user, "id", None),
        getattr(request.user, "username", None),
    )

    if user_is_global_admin(request.user):
        empresa = _resolver_empresa_contexto_global(request)
        if not empresa:
            messages.error(request, "Não existem empresas disponíveis para carregar o dashboard.")
            return None

        logger.info(
            "Acesso ao dashboard concedido via administração global. user_id=%s, empresa_id=%s",
            request.user.id,
            empresa.id,
        )
        return SimpleNamespace(
            pk=request.user.id,
            empresa=empresa,
            empresa_id=empresa.id,
            tipo_acesso="global_admin",
        )

    perfil = obter_contexto_admin_projetos(request.user)

    if perfil and perfil.empresa_id:
        logger.info(
            "Acesso ao dashboard concedido via PerfilPlataforma. user_id=%s, perfil_id=%s, tipo_acesso='%s', empresa_id=%s",
            request.user.id,
            perfil.pk,
            perfil.tipo_acesso,
            perfil.empresa_id,
        )
        return perfil

    logger.warning(
        "Acesso ao dashboard bloqueado: sem registo operacional e sem perfil de empresa válido. user_id=%s",
        getattr(request.user, "id", None),
    )
    messages.error(
        request,
        "A tua conta não está ligada a um registo operacional nem a uma empresa válida. Contacta o administrador.",
    )
    return None



def _obter_empresa_dashboard(contexto_admin):
    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if empresa is not None:
        return empresa

    if not empresa_id:
        logger.warning(
            "Não foi possível obter empresa_id para o dashboard. objeto_tipo='%s', objeto_id=%s",
            contexto_admin.__class__.__name__,
            getattr(contexto_admin, "pk", None),
        )
        return None

    empresa = obter_empresa_dashboard_por_id(empresa_id)
    if not empresa:
        logger.warning(
            "Empresa do dashboard não encontrada. objeto_tipo='%s', objeto_id=%s, empresa_id=%s",
            contexto_admin.__class__.__name__,
            getattr(contexto_admin, "pk", None),
            empresa_id,
        )
        return None

    return empresa



def _montar_contexto_dashboard(request, contexto_admin, incluir_mapa=False):
    empresa = _obter_empresa_dashboard(contexto_admin)

    if not empresa:
        logger.warning(
            "Montagem do contexto do dashboard falhou: empresa não determinada. user_id=%s",
            request.user.id,
        )
        messages.error(request, "Não foi possível determinar a empresa associada a esta conta.")
        return {"filtros": {}}

    if not user_is_global_admin(request.user) and not empresa.pode_aceder_dashboard_empresa():
        logger.warning(
            "Acesso ao dashboard bloqueado por restrição do plano. user_id=%s, empresa_id=%s, plano_id=%s",
            request.user.id,
            empresa.id,
            empresa.plano_id,
        )
        messages.error(request, "O plano atual desta empresa não permite acesso ao dashboard de empresa.")
        return {"filtros": {}}

    try:
        inicio, fim, projeto_id, empregado_id = obter_intervalo_filtros(
            request,
            empresa=empresa,
        )

        filtros = {
            "periodo": request.GET.get("periodo", "30_dias"),
            "data_inicio": request.GET.get("data_inicio", ""),
            "data_fim": request.GET.get("data_fim", ""),
            "projeto": request.GET.get("projeto", ""),
            "empregado": request.GET.get("empregado", ""),
            "empresa": str(empresa.id),
        }

        context = {
            "filtros": filtros,
            "empresa_dashboard": empresa,
            "empresa_contexto": empresa,
        }

        if user_is_global_admin(request.user):
            context["empresas_contexto"] = obter_empresas_contexto_dashboard()

        if incluir_mapa:
            context["projetos"] = obter_projetos_mapa(empresa=empresa)

        context.update(obter_opcoes_filtros_dashboard(empresa=empresa))
        context.update(
            obter_cards_dashboard(
                inicio=inicio,
                fim=fim,
                projeto_id=projeto_id,
                empregado_id=empregado_id,
                empresa=empresa,
            )
        )
        context.update(
            obter_alertas_dashboard(
                inicio=inicio,
                fim=fim,
                projeto_id=projeto_id,
                empregado_id=empregado_id,
                empresa=empresa,
            )
        )
        context.update(
            obter_graficos_dashboard(
                inicio=inicio,
                fim=fim,
                projeto_id=projeto_id,
                empregado_id=empregado_id,
                empresa=empresa,
            )
        )

        logger.info(
            "Contexto do dashboard montado com sucesso. user_id=%s, empresa_id=%s, incluir_mapa=%s, projeto_id=%s, empregado_id=%s",
            request.user.id,
            empresa.id,
            incluir_mapa,
            projeto_id,
            empregado_id,
        )
        return context

    except Exception:
        logger.error(
            "Erro ao montar contexto do dashboard. user_id=%s, empresa_id=%s, incluir_mapa=%s",
            request.user.id,
            empresa.id,
            incluir_mapa,
            exc_info=True,
        )
        messages.error(request, "Ocorreu um erro ao carregar o dashboard.")
        return {"filtros": {}}


@login_required
def graficos_dashboard(request):
    logger.info(
        "Entrada na view graficos_dashboard. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    contexto_admin = _obter_contexto_admin_dashboard(request)
    if contexto_admin is None:
        logger.warning(
            "Redirecionamento em graficos_dashboard por falta de contexto administrativo. user_id=%s",
            request.user.id,
        )
        return redirect("projetos:redirect_after_login")

    context = _montar_contexto_dashboard(
        request,
        contexto_admin,
        incluir_mapa=False,
    )

    if not context.get("empresa_dashboard"):
        return redirect("projetos:redirect_after_login")

    return render(request, "projetos/graficos_dashboard.html", context)


@login_required
def dashboard(request):
    logger.info(
        "Entrada na view dashboard. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    contexto_admin = _obter_contexto_admin_dashboard(request)
    if contexto_admin is None:
        logger.warning(
            "Redirecionamento em dashboard por falta de contexto administrativo. user_id=%s",
            request.user.id,
        )
        return redirect("projetos:redirect_after_login")

    context = _montar_contexto_dashboard(
        request,
        contexto_admin,
        incluir_mapa=True,
    )

    if not context.get("empresa_dashboard"):
        return redirect("projetos:redirect_after_login")

    return render(request, "projetos/dashboard.html", context)
