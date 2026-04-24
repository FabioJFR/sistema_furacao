import hashlib
import json
from datetime import date, datetime
from decimal import Decimal

from projetos.models import FuroVersao


def _serialize_json(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def construir_snapshot_furo(furo):
    return {
        "furo_id": str(furo.pk),
        "empresa_id": str(furo.empresa_id) if furo.empresa_id else None,
        "projeto_id": str(furo.projeto_id) if furo.projeto_id else None,
        "nome": furo.nome,
        "estado": furo.estado,
        "tipo": furo.tipo,
        "profundidade_inicial": float(furo.profundidade_inicial or 0),
        "profundidade_alvo_inicial": float(furo.profundidade_alvo_inicial or 0),
        "profundidade_alvo_atual": float(furo.profundidade_alvo_atual or 0),
        "profundidade_atual": float(furo.profundidade_atual or 0),
        "profundidade_maxima_atingida": float(furo.profundidade_maxima_atingida or 0),
        "inclinacao_planeada_inicial": float(furo.inclinacao_planeada_inicial or 0),
        "inclinacao_planeada_atual": float(furo.inclinacao_planeada_atual or 0),
        "inclinacao_real_atual": float(furo.inclinacao_real_atual or 0),
        "azimute_planeado_inicial": float(furo.azimute_planeado_inicial or 0),
        "azimute_planeado_atual": float(furo.azimute_planeado_atual or 0),
        "azimute_real_atual": float(furo.azimute_real_atual or 0),
        "magnetismo": float(furo.magnetismo or 0),
        "latitude": furo.latitude,
        "longitude": furo.longitude,
        "altitude": furo.altitude,
        "localizacao": furo.localizacao or "",
        "local_sondagem": furo.local_sondagem or "",
        "origem_este": float(furo.origem_este or 0),
        "origem_norte": float(furo.origem_norte or 0),
        "origem_tvd": float(furo.origem_tvd or 0),
        "metros_furados": float(furo.metros_furados or 0),
        "total_horas_segundos": float(furo.total_horas.total_seconds()) if furo.total_horas else 0,
    }


def calcular_hash_snapshot(snapshot):
    payload = json.dumps(snapshot, sort_keys=True, default=_serialize_json, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _proxima_versao_numero(furo):
    ultima = (
        FuroVersao.objects.filter(furo=furo)
        .order_by("-versao_numero")
        .only("versao_numero")
        .first()
    )
    return (ultima.versao_numero + 1) if ultima else 1


def registar_versao_furo(furo, *, origem="atualizado", criado_por=None, observacoes=""):
    snapshot = construir_snapshot_furo(furo)
    hash_estado = calcular_hash_snapshot(snapshot)
    ultima = (
        FuroVersao.objects.filter(furo=furo)
        .order_by("-versao_numero")
        .only("hash_estado", "versao_numero")
        .first()
    )

    if ultima and ultima.hash_estado == hash_estado:
        return None

    versao = FuroVersao.objects.create(
        empresa=furo.empresa,
        projeto=furo.projeto,
        furo=furo,
        versao_numero=_proxima_versao_numero(furo),
        origem=origem,
        hash_estado=hash_estado,
        dados_snapshot=snapshot,
        criado_por=criado_por,
        observacoes=observacoes or "",
    )
    return versao

