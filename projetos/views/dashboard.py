from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.permissions import admin_required
from projetos.selectors.dashboard import (
    obter_alertas_dashboard,
    obter_cards_dashboard,
    obter_graficos_dashboard,
    obter_intervalo_filtros,
    obter_opcoes_filtros_dashboard,
)
from projetos.selectors.projetos import obter_projetos_mapa

@login_required
@admin_required
def graficos_dashboard(request):
    inicio, fim, projeto_id, empregado_id = obter_intervalo_filtros(request)

    filtros = {
        "periodo": request.GET.get("periodo", "30_dias"),
        "data_inicio": request.GET.get("data_inicio", ""),
        "data_fim": request.GET.get("data_fim", ""),
        "projeto": request.GET.get("projeto", ""),
        "empregado": request.GET.get("empregado", ""),
    }

    context = {
        "filtros": filtros,
    }

    context.update(obter_opcoes_filtros_dashboard())
    context.update(
        obter_cards_dashboard(
            inicio=inicio,
            fim=fim,
            projeto_id=projeto_id,
            empregado_id=empregado_id,
        )
    )
    context.update(
        obter_alertas_dashboard(
            inicio=inicio,
            fim=fim,
            projeto_id=projeto_id,
            empregado_id=empregado_id,
        )
    )
    context.update(
        obter_graficos_dashboard(
            inicio=inicio,
            fim=fim,
            projeto_id=projeto_id,
            empregado_id=empregado_id,
        )
    )

    return render(request, "projetos/graficos_dashboard.html", context)


@login_required
@admin_required
def dashboard(request):
    inicio, fim, projeto_id, empregado_id = obter_intervalo_filtros(request)

    filtros = {
        "periodo": request.GET.get("periodo", "30_dias"),
        "data_inicio": request.GET.get("data_inicio", ""),
        "data_fim": request.GET.get("data_fim", ""),
        "projeto": request.GET.get("projeto", ""),
        "empregado": request.GET.get("empregado", ""),
    }

    context = {
        "filtros": filtros,
        "projetos": obter_projetos_mapa(),
    }

    context.update(obter_opcoes_filtros_dashboard())
    context.update(
        obter_cards_dashboard(
            inicio=inicio,
            fim=fim,
            projeto_id=projeto_id,
            empregado_id=empregado_id,
        )
    )
    context.update(
        obter_alertas_dashboard(
            inicio=inicio,
            fim=fim,
            projeto_id=projeto_id,
            empregado_id=empregado_id,
        )
    )
    context.update(
        obter_graficos_dashboard(
            inicio=inicio,
            fim=fim,
            projeto_id=projeto_id,
            empregado_id=empregado_id,
        )
    )

    return render(request, "projetos/dashboard.html", context)