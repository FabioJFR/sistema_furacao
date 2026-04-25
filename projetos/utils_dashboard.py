from django.utils import timezone

from projetos.selectors.dashboard import (
    aplicar_filtros_registos as aplicar_filtros_registos_selector,
    obter_alertas_dashboard as obter_alertas_dashboard_selector,
    obter_cards_dashboard as obter_cards_dashboard_selector,
    obter_graficos_dashboard as obter_graficos_dashboard_selector,
    obter_intervalo_filtros as obter_intervalo_filtros_selector,
    obter_opcoes_filtros_dashboard as obter_opcoes_filtros_dashboard_selector,
)


def obter_intervalo_filtros(request, empresa=None):
    inicio, fim, projeto_id, empregado_id = obter_intervalo_filtros_selector(request, empresa=empresa)
    return {
        "periodo": request.GET.get("periodo", "30_dias"),
        "inicio": inicio,
        "fim": fim,
        "data_inicio": request.GET.get("data_inicio") or "",
        "data_fim": request.GET.get("data_fim") or "",
        "projeto_id": projeto_id or "",
        "empregado_id": empregado_id or "",
    }


def obter_cards_dashboard(inicio=None, fim=None, projeto_id=None, empregado_id=None, empresa=None):
    return obter_cards_dashboard_selector(
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
        empresa=empresa,
    )


def obter_alertas_dashboard(inicio=None, fim=None, projeto_id=None, empregado_id=None, empresa=None):
    return obter_alertas_dashboard_selector(
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
        empresa=empresa,
    )


def obter_opcoes_filtros_dashboard(empresa=None):
    return obter_opcoes_filtros_dashboard_selector(empresa=empresa)


def aplicar_filtros_registos(queryset, inicio=None, fim=None, projeto_id=None, empregado_id=None, empresa=None):
    return aplicar_filtros_registos_selector(
        queryset,
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
        empresa=empresa,
    )


def obter_graficos_dashboard(inicio=None, fim=None, projeto_id=None, empregado_id=None, empresa=None, request=None):
    if fim is None:
        fim = timezone.now().date()
    return obter_graficos_dashboard_selector(
        inicio=inicio,
        fim=fim,
        projeto_id=projeto_id,
        empregado_id=empregado_id,
        empresa=empresa,
        request=request,
    )
