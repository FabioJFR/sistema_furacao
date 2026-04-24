from django.db.models import Count

from projetos.models import EventoAnalytics


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def _queryset_eventos_empresa(empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return (
        EventoAnalytics.objects.filter(empresa_id=empresa_id)
        .select_related("projeto", "furo", "empregado", "material", "maquina", "actor_user")
        .order_by("-criado_em")
    )


def obter_eventos_analytics_filtrados(empresa, filtros):
    filtros = filtros or {}
    queryset = _queryset_eventos_empresa(empresa)

    tipo_evento = (filtros.get("tipo_evento") or "").strip()
    entidade_tipo = (filtros.get("entidade_tipo") or "").strip()
    projeto = (filtros.get("projeto") or "").strip()
    furo = (filtros.get("furo") or "").strip()

    if tipo_evento:
        queryset = queryset.filter(tipo_evento=tipo_evento)
    if entidade_tipo:
        queryset = queryset.filter(entidade_tipo=entidade_tipo)
    if projeto:
        queryset = queryset.filter(projeto_id=projeto)
    if furo:
        queryset = queryset.filter(furo_id=furo)

    return queryset


def obter_entidades_analytics_disponiveis(empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return (
        EventoAnalytics.objects.filter(empresa_id=empresa_id)
        .values_list("entidade_tipo", flat=True)
        .distinct()
        .order_by("entidade_tipo")
    )


def obter_resumo_tipos_evento_analytics(empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return {
        item["tipo_evento"]: item["total"]
        for item in (
            EventoAnalytics.objects.filter(empresa_id=empresa_id)
            .values("tipo_evento")
            .annotate(total=Count("id"))
        )
    }
