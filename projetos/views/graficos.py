from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from core.permissions import admin_required
from projetos.selectors.dashboard import (
    obter_intervalo_filtros,
    obter_cards_dashboard,
    obter_alertas_dashboard,
    obter_graficos_dashboard,
)


@login_required
@admin_required
def graficos_dashboard(request):
    inicio, fim, projeto_id, empregado_id = obter_intervalo_filtros(request)

    context = {
        "filtros": {
            "periodo": request.GET.get("periodo", "30_dias"),
            "data_inicio": request.GET.get("data_inicio", ""),
            "data_fim": request.GET.get("data_fim", ""),
            "projeto": request.GET.get("projeto", ""),
            "empregado": request.GET.get("empregado", ""),
        }
    }

    context.update(obter_cards_dashboard())
    context.update(obter_alertas_dashboard())
    context.update(
        obter_graficos_dashboard(
            inicio=inicio,
            fim=fim,
            projeto_id=projeto_id,
            empregado_id=empregado_id,
        )
    )

    return render(request, "projetos/graficos_dashboard.html", context)