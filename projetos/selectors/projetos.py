from django.shortcuts import get_object_or_404

from projetos.models import Medicao, Projeto


def obter_projetos_mapa():
    projetos_qs = Projeto.objects.all().order_by("nome")

    projetos = []
    for p in projetos_qs:
        projetos.append({
            "id": str(p.id),
            "nome": p.nome,
            "cidade": p.cidade,
            "pais": p.pais,
            "status": p.status,
            "localizacao_lat": float(p.localizacao_lat) if p.localizacao_lat is not None else None,
            "localizacao_lon": float(p.localizacao_lon) if p.localizacao_lon is not None else None,
        })

    return projetos


def obter_lista_projetos():
    return Projeto.objects.all().order_by("nome")


def obter_projeto(pk):
    return get_object_or_404(Projeto, pk=pk)


def obter_contexto_projeto_detail(pk):
    projeto = get_object_or_404(
        Projeto.objects.prefetch_related(
            "furos",
            "materiais",
            "maquinas",
            "levantamentos_materiais",
            "registos_projeto",
        ),
        pk=pk,
    )

    furos = projeto.furos.all().order_by("nome")

    furos_mapa = []
    for furo in furos:
        if furo.latitude is None or furo.longitude is None:
            continue

        furos_mapa.append({
            "id": str(furo.id),
            "nome": furo.nome,
            "profundidade_atual": furo.profundidade_atual or 0,
            "profundidade_alvo_inicial": furo.profundidade_alvo_inicial or 0,
            "profundidade_alvo_atual": furo.profundidade_alvo_atual or 0,
            "inclinacao_planeada_inicial": (
                furo.inclinacao_planeada_inicial
                if furo.inclinacao_planeada_inicial is not None else "-"
            ),
            "azimute_planeado_inicial": (
                furo.azimute_planeado_inicial
                if furo.azimute_planeado_inicial is not None else "-"
            ),
            "lat": float(furo.latitude),
            "lon": float(furo.longitude),
        })

    levantamentos = projeto.levantamentos_materiais.select_related(
        "empregado", "material", "furo"
    ).all()

    registos = projeto.registos_projeto.select_related(
        "empregado", "furo"
    ).all()

    return {
        "projeto": projeto,
        "furos": furos,
        "furos_mapa": furos_mapa,
        "levantamentos": levantamentos,
        "materiais": projeto.materiais.all(),
        "maquinas": projeto.maquinas.all(),
        "registos": registos,
        "projeto_mapa": {
            "nome": projeto.nome,
            "cidade": projeto.cidade,
            "pais": projeto.pais,
            "lat": float(projeto.localizacao_lat) if projeto.localizacao_lat is not None else None,
            "lon": float(projeto.localizacao_lon) if projeto.localizacao_lon is not None else None,
        },
    }


def obter_furos_projeto(projeto):
    return projeto.furos.all().order_by("nome")


def obter_medicoes_projeto(projeto):
    return (
        Medicao.objects
        .filter(furo__projeto=projeto)
        .select_related("furo")
        .order_by("criado_em", "profundidade_medida")
    )


def obter_dados_3d_projeto(projeto):
    furos = projeto.furos.all().order_by("nome")

    dados_furos = []

    for furo in furos:
        dados_furos.append({
            "id": str(furo.id),
            "nome": furo.nome,
            "origem_este": furo.origem_este or 0,
            "origem_norte": furo.origem_norte or 0,
            "origem_tvd": furo.origem_tvd or 0,
            "profundidade_inicial": furo.profundidade_inicial or 0,
            "profundidade_atual": furo.profundidade_atual or 0,
            "profundidade_maxima_atingida": furo.profundidade_maxima_atingida or 0,
            "profundidade_alvo_inicial": furo.profundidade_alvo_inicial or 0,
            "profundidade_alvo_atual": furo.profundidade_alvo_atual or 0,
            "inclinacao_planeada_inicial": furo.inclinacao_planeada_inicial or 0,
            "inclinacao_planeada_atual": furo.inclinacao_planeada_atual or 0,
            "azimute_planeado_inicial": furo.azimute_planeado_inicial or 0,
            "azimute_planeado_atual": furo.azimute_planeado_atual or 0,
            "inclinacao_real_atual": furo.inclinacao_real_atual or 0,
            "azimute_real_atual": furo.azimute_real_atual or 0,
            "estado": furo.estado,
        })

    return dados_furos