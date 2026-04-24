import math

from django.db.models import Sum

from projetos.models import Despesa, Furo


FURO_MEMORY_RADIUS_KM = 0.35


def parse_float_or_none(value):
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _distancia_km(lat1, lon1, lat2, lon2):
    if None in {lat1, lon1, lat2, lon2}:
        return None

    raio = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * raio * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def obter_memoria_zona_furos(*, empresa_id, latitude=None, longitude=None, localizacao=None, excluir_furo_id=None, limite=6):
    candidatos = (
        Furo.objects.filter(empresa_id=empresa_id)
        .select_related("projeto")
        .prefetch_related("medicoes", "registos_furo")
    )
    if excluir_furo_id:
        candidatos = candidatos.exclude(pk=excluir_furo_id)

    localizacao_ref = (localizacao or "").strip().lower()
    encontrados = []

    for candidato in candidatos:
        distancia = _distancia_km(latitude, longitude, candidato.latitude, candidato.longitude)
        correspondencia_local = False

        if localizacao_ref:
            candidato_local = (candidato.localizacao or candidato.local_sondagem or "").strip().lower()
            correspondencia_local = bool(candidato_local and candidato_local == localizacao_ref)

        if distancia is None and not correspondencia_local:
            continue
        if distancia is not None and distancia > FURO_MEMORY_RADIUS_KM and not correspondencia_local:
            continue

        total_despesas = float(
            Despesa.objects.filter(furo=candidato).aggregate(total=Sum("valor")).get("total") or 0
        )
        encontrados.append(
            {
                "id": str(candidato.pk),
                "nome": candidato.nome,
                "projeto": candidato.projeto.nome if candidato.projeto_id else "-",
                "estado": candidato.get_estado_display(),
                "localizacao": candidato.localizacao or candidato.local_sondagem or "-",
                "distancia_km": round(distancia, 3) if distancia is not None else None,
                "mesma_localizacao_textual": correspondencia_local,
                "profundidade_maxima_atingida": float(candidato.profundidade_maxima_atingida or 0),
                "metros_furados": float(candidato.metros_furados or 0),
                "total_medicoes": candidato.medicoes.count(),
                "total_registos": candidato.registos_furo.count(),
                "total_despesas": round(total_despesas, 2),
            }
        )

    encontrados.sort(
        key=lambda item: (
            0 if item["mesma_localizacao_textual"] else 1,
            item["distancia_km"] if item["distancia_km"] is not None else 999999,
        )
    )
    return encontrados[:limite]
