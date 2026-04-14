from django.shortcuts import get_object_or_404

from projetos.models import ConfiguracaoPerfuracaoEmpregado, Furo, Medicao


def obter_equipa_e_configuracao_por_furo(furo):
    configuracoes = (
        ConfiguracaoPerfuracaoEmpregado.objects
        .filter(furo=furo)
        .select_related("empregado", "furo", "atualizado_por")
        .order_by("empregado__nome")
    )
    return configuracoes


def obter_lista_furos():
    return Furo.objects.select_related("projeto").order_by("nome")


def obter_furo(pk):
    return get_object_or_404(
        Furo.objects.select_related("projeto"),
        pk=pk,
    )


def obter_contexto_detalhe_furo(pk):
    furo = get_object_or_404(
        Furo.objects.select_related("projeto").prefetch_related(
            "medicoes",
            "registos_furo",
            "levantamentos_materiais",
        ),
        pk=pk,
    )

    medicoes = furo.medicoes.all().order_by("criado_em", "profundidade_medida")
    registos = (
        furo.registos_furo
        .select_related("empregado", "projeto")
        .all()
        .order_by("-data", "-criado_em")
    )

    furo_mapa = {
        "id": str(furo.id),
        "nome": furo.nome,
        "lat": float(furo.latitude) if furo.latitude is not None else None,
        "lon": float(furo.longitude) if furo.longitude is not None else None,
        "projeto": furo.projeto.nome if furo.projeto else "",
        "profundidade_atual": furo.profundidade_atual or 0,
        "profundidade_alvo_inicial": furo.profundidade_alvo_inicial or 0,
        "profundidade_alvo_atual": furo.profundidade_alvo_atual or 0,
        "inclinacao_planeada_inicial": (
            furo.inclinacao_planeada_inicial
            if furo.inclinacao_planeada_inicial is not None else "-"
        ),
        "inclinacao_planeada_atual": (
            furo.inclinacao_planeada_atual
            if furo.inclinacao_planeada_atual is not None else "-"
        ),
        "azimute_planeado_inicial": (
            furo.azimute_planeado_inicial
            if furo.azimute_planeado_inicial is not None else "-"
        ),
        "azimute_planeado_atual": (
            furo.azimute_planeado_atual
            if furo.azimute_planeado_atual is not None else "-"
        ),
        "inclinacao_real_atual": (
            furo.inclinacao_real_atual
            if furo.inclinacao_real_atual is not None else "-"
        ),
        "azimute_real_atual": (
            furo.azimute_real_atual
            if furo.azimute_real_atual is not None else "-"
        ),
    }

    levantamentos = (
        furo.levantamentos_materiais
        .select_related("empregado", "material", "projeto")
        .all()
    )

    return {
        "furo": furo,
        "medicoes": medicoes,
        "registos": registos,
        "levantamentos": levantamentos,
        "furo_mapa": furo_mapa,
    }


def obter_medicoes_furo(furo):
    return Medicao.objects.filter(furo=furo).order_by("criado_em", "profundidade_medida")