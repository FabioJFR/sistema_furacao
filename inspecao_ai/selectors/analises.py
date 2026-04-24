from django.shortcuts import get_object_or_404

from inspecao_ai.models import AnaliseImagemAI, AnaliseZonaPresetAI


def listar_analises_empresa_qs(empresa):
    return (
        AnaliseImagemAI.objects.filter(empresa=empresa)
        .select_related("projeto", "furo", "criado_por")
        .prefetch_related("deteccoes")
    )


def listar_analises_recentes_hub_qs(empresa):
    return listar_analises_empresa_qs(empresa).order_by("-criado_em")


def listar_presets_zona_empresa(empresa):
    return list(
        AnaliseZonaPresetAI.objects.filter(empresa=empresa)
        .order_by("tipo_documento", "nome")
        .values("id", "nome", "tipo_documento", "zona_relatorio", "zonas_texto")
    )


def obter_analise_empresa(pk, empresa):
    return get_object_or_404(AnaliseImagemAI, pk=pk, empresa=empresa)


def obter_analise_detail_empresa(pk, empresa):
    return get_object_or_404(
        listar_analises_empresa_qs(empresa),
        pk=pk,
    )


def obter_analise_reprocessar_empresa(pk, empresa):
    return get_object_or_404(
        AnaliseImagemAI.objects.select_related("projeto", "furo", "criado_por"),
        pk=pk,
        empresa=empresa,
    )
