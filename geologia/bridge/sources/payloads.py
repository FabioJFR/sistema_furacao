from datetime import UTC, datetime


def utc_iso():
    return datetime.now(UTC).isoformat()


def normalize_external_payload(payload, default_estado="em_voo", default_bridge_status="online"):
    payload = payload or {}

    aliases = {
        "lat": "latitude",
        "lon": "longitude",
        "alt": "altitude_m",
        "vel": "velocidade_ms",
        "gps": "gps_satellites",
        "bateria": "bateria_percent",
        "sinal": "sinal_percent",
        "estado": "estado_conexao",
        "bridge_status": "estado_bridge",
    }
    normalized = {}

    for key, value in payload.items():
        normalized[aliases.get(key, key)] = value

    normalized.setdefault("estado_conexao", default_estado)
    normalized.setdefault("estado_bridge", default_bridge_status)
    normalized.setdefault("recording", False)
    normalized["updated_at"] = payload.get("updated_at") or utc_iso()
    return normalized
