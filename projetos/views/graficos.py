import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.permissions import admin_required
from django.shortcuts import redirect, render

from plataforma.models import PerfilPlataforma
from projetos.models import Empregados
from projetos.selectors.dashboard import (
    obter_alertas_dashboard,
    obter_cards_dashboard,
    obter_graficos_dashboard,
    obter_intervalo_filtros,
)

logger = logging.getLogger("core")

ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


# TODO futuro:
# - unificar esta lógica com `projetos/views/dashboard.py` para evitar duplicação
# - criar decorator próprio para administradores da app projetos (empresa_admin / empresa_gestor)
# - criar automaticamente o registo Empregados para administradores de empresa no onboarding
# - deixar de depender de Empregados para permissões administrativas da app projetos


def _obter_admin_empregado_graficos(request):
    logger.debug(
        "A verificar acesso aos gráficos: user_id=%s, username='%s'",
        getattr(request.user, "id", None),
        getattr(request.user, "username", None),
    )

    perfil = PerfilPlataforma.objects.filter(
        user=request.user,
        ativo=True,
        tipo_acesso__in=ADMIN_TIPOS_ACESSO_EMPRESA,
    ).select_related("empresa").first()

    if perfil and perfil.empresa_id:
        logger.info(
            "Acesso aos gráficos concedido via PerfilPlataforma. user_id=%s, perfil_id=%s, tipo_acesso='%s', empresa_id=%s",
            request.user.id,
            perfil.pk,
            perfil.tipo_acesso,
            perfil.empresa_id,
        )
        return perfil

    logger.warning(
        "Acesso aos gráficos bloqueado: sem registo operacional e sem perfil de empresa válido. user_id=%s",
        getattr(request.user, "id", None),
    )
    messages.error(
        request,
        "A tua conta não está ligada a um registo operacional nem a uma empresa válida. Contacta o administrador.",
    )
    return None



def _obter_empresa_graficos(admin_empregado):
    empresa = getattr(admin_empregado, "empresa", None)
    empresa_id = getattr(admin_empregado, "empresa_id", None)

    if not empresa_id:
        logger.warning(
            "Não foi possível obter empresa_id para os gráficos. objeto_tipo='%s', objeto_id=%s",
            admin_empregado.__class__.__name__,
            getattr(admin_empregado, "pk", None),
        )
        return None

    return empresa or empresa_id


@login_required
@admin_required
def graficos_dashboard(request):
    logger.info(
        "Entrada na view graficos_dashboard. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    admin_empregado = _obter_admin_empregado_graficos(request)
    if admin_empregado is None:
        logger.warning(
            "Redirecionamento em graficos_dashboard por falta de contexto administrativo. user_id=%s",
            request.user.id,
        )
        return redirect("projetos:redirect_after_login")

    empresa = _obter_empresa_graficos(admin_empregado)
    if not empresa:
        logger.warning(
            "Não foi possível determinar a empresa associada aos gráficos. user_id=%s",
            request.user.id,
        )
        messages.error(request, "Não foi possível determinar a empresa associada a esta conta.")
        return redirect("projetos:redirect_after_login")

    try:
        inicio, fim, projeto_id, empregado_id = obter_intervalo_filtros(
            request,
            empresa=empresa,
        )

        context = {
            "filtros": {
                "periodo": request.GET.get("periodo", "30_dias"),
                "data_inicio": request.GET.get("data_inicio", ""),
                "data_fim": request.GET.get("data_fim", ""),
                "projeto": request.GET.get("projeto", ""),
                "empregado": request.GET.get("empregado", ""),
            }
        }

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
            "Contexto dos gráficos montado com sucesso. user_id=%s, empresa_id=%s, projeto_id=%s, empregado_id=%s",
            request.user.id,
            getattr(empresa, "pk", empresa),
            projeto_id,
            empregado_id,
        )
        return render(request, "projetos/graficos_dashboard.html", context)

    except Exception:
        logger.error(
            "Erro ao carregar gráficos. user_id=%s, empresa_id=%s",
            request.user.id,
            getattr(empresa, "pk", empresa),
            exc_info=True,
        )
        messages.error(request, "Ocorreu um erro ao carregar os gráficos.")
        return redirect("projetos:dashboard")
