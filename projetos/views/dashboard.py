import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from projetos.services.dashboard_contexto import (
    montar_contexto_dashboard,
    obter_contexto_admin_dashboard,
)

logger = logging.getLogger("core")


def _render_analytics_dashboard(request, *, mode):
    contexto_admin = obter_contexto_admin_dashboard(request)
    if contexto_admin is None:
        logger.warning(
            "Redirecionamento em analytics mode=%s por falta de contexto administrativo. user_id=%s",
            mode,
            request.user.id,
        )
        return redirect("projetos:redirect_after_login")

    context = montar_contexto_dashboard(
        request=request,
        contexto_admin=contexto_admin,
        incluir_mapa=False,
    )
    if not context.get("empresa_dashboard"):
        return redirect("projetos:redirect_after_login")

    # Defaults
    context["analytics_mode"] = mode
    context["mostrar_operacional_metricas"] = False
    context["mostrar_operacional_alertas"] = False
    context["mostrar_operacional_graficos"] = False
    context["mostrar_financeiro_metricas"] = False
    context["mostrar_financeiro_quadros"] = False
    context["mostrar_financeiro_graficos"] = False

    if mode == "operacional":
        context["mostrar_operacional_metricas"] = True
        context["mostrar_operacional_alertas"] = True
        context["mostrar_operacional_graficos"] = True
    elif mode == "financeiro":
        context["mostrar_financeiro_metricas"] = True
        context["mostrar_financeiro_quadros"] = True
        context["mostrar_financeiro_graficos"] = True
    elif mode == "rentabilidade":
        context["mostrar_financeiro_metricas"] = True
        context["mostrar_financeiro_quadros"] = True
    elif mode == "produtividade":
        context["mostrar_operacional_metricas"] = True
        context["mostrar_operacional_graficos"] = True
    elif mode == "alertas":
        context["mostrar_operacional_alertas"] = True
    else:
        context["mostrar_operacional_metricas"] = True
        context["mostrar_operacional_alertas"] = True
        context["mostrar_operacional_graficos"] = True
        context["mostrar_financeiro_metricas"] = True
        context["mostrar_financeiro_quadros"] = True
        context["mostrar_financeiro_graficos"] = True

    return render(request, "projetos/graficos_dashboard.html", context)


@login_required
def graficos_dashboard(request):
    logger.info(
        "Entrada na view graficos_dashboard. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    return _render_analytics_dashboard(request, mode="all")


@login_required
def graficos_operacionais_dashboard(request):
    logger.info(
        "Entrada na view graficos_operacionais_dashboard. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    return _render_analytics_dashboard(request, mode="operacional")


@login_required
def graficos_financeiros_dashboard(request):
    logger.info(
        "Entrada na view graficos_financeiros_dashboard. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    return _render_analytics_dashboard(request, mode="financeiro")


@login_required
def graficos_rentabilidade_dashboard(request):
    logger.info(
        "Entrada na view graficos_rentabilidade_dashboard. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    return _render_analytics_dashboard(request, mode="rentabilidade")


@login_required
def graficos_produtividade_dashboard(request):
    logger.info(
        "Entrada na view graficos_produtividade_dashboard. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    return _render_analytics_dashboard(request, mode="produtividade")


@login_required
def graficos_alertas_dashboard(request):
    logger.info(
        "Entrada na view graficos_alertas_dashboard. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    return _render_analytics_dashboard(request, mode="alertas")


@login_required
def dashboard(request):
    logger.info(
        "Entrada na view dashboard. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    contexto_admin = obter_contexto_admin_dashboard(request)
    if contexto_admin is None:
        logger.warning(
            "Redirecionamento em dashboard por falta de contexto administrativo. user_id=%s",
            request.user.id,
        )
        return redirect("projetos:redirect_after_login")

    context = montar_contexto_dashboard(
        request=request,
        contexto_admin=contexto_admin,
        incluir_mapa=True,
    )

    if not context.get("empresa_dashboard"):
        return redirect("projetos:redirect_after_login")

    return render(request, "projetos/dashboard.html", context)
