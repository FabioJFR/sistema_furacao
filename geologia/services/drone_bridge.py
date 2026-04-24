import json
import urllib.request

from django.utils import timezone

from geologia.models import DroneOperacaoTempoReal


def append_bridge_log(operacao, mensagem, tipo="info"):
    if operacao is None or not mensagem:
        return
    metadados = dict(operacao.metadados or {})
    logs = list(metadados.get("bridge_logs") or [])
    logs.insert(
        0,
        {
            "mensagem": str(mensagem),
            "tipo": tipo,
            "timestamp": timezone.now().isoformat(),
        },
    )
    metadados["bridge_logs"] = logs[:40]
    operacao.metadados = metadados


def set_bridge_meta(operacao, key, value):
    if operacao is None:
        return
    metadados = dict(operacao.metadados or {})
    metadados[key] = value
    operacao.metadados = metadados


def bridge_headers(operacao):
    headers = {"Accept": "application/json"}
    if operacao.bridge_api_key:
        headers["X-Bridge-Key"] = operacao.bridge_api_key
    return headers


def normalizar_estado_bridge(operacao, payload):
    if not isinstance(payload, dict):
        return

    estado_bridge = payload.get("estado_bridge") or payload.get("bridge_status") or ""
    if estado_bridge:
        operacao.bridge_ultimo_estado = str(estado_bridge)[:120]

    operacao.live_view_url = payload.get("live_view_url") or payload.get("stream_url") or operacao.live_view_url
    operacao.frame_snapshot_url = payload.get("frame_snapshot_url") or payload.get("snapshot_url") or operacao.frame_snapshot_url
    operacao.latitude_atual = payload.get("latitude_atual", payload.get("latitude", operacao.latitude_atual))
    operacao.longitude_atual = payload.get("longitude_atual", payload.get("longitude", operacao.longitude_atual))
    operacao.altitude_atual_m = payload.get("altitude_atual_m", payload.get("altitude_m", operacao.altitude_atual_m))
    operacao.velocidade_atual_ms = payload.get("velocidade_atual_ms", payload.get("velocidade_ms", operacao.velocidade_atual_ms))
    operacao.heading_graus = payload.get("heading_graus", payload.get("heading", operacao.heading_graus))
    operacao.bateria_percent = payload.get("bateria_percent", operacao.bateria_percent)
    operacao.sinal_percent = payload.get("sinal_percent", operacao.sinal_percent)
    operacao.satelites_gps = payload.get("satelites_gps", payload.get("gps_satellites", operacao.satelites_gps))
    operacao.gravacao_ativa = bool(payload.get("gravacao_ativa", payload.get("recording", operacao.gravacao_ativa)))
    operacao.ultimo_heartbeat = timezone.now()
    operacao.bridge_ultima_sincronizacao = timezone.now()
    operacao.bridge_ultimo_erro = ""

    estado_conexao = payload.get("estado_conexao")
    if estado_conexao in dict(DroneOperacaoTempoReal.ESTADO_CONEXAO_CHOICES):
        operacao.estado_conexao = estado_conexao
    elif operacao.live_view_url or operacao.frame_snapshot_url:
        operacao.estado_conexao = "pronto"
    else:
        operacao.estado_conexao = "procurando"

    operacao.metadados = {
        **(operacao.metadados or {}),
        "bridge_payload_mais_recente": payload,
    }


def buscar_estado_bridge(operacao, path="/health"):
    if not operacao.bridge_ativa or not operacao.bridge_base_url:
        raise ValueError("Bridge não configurada.")

    url = operacao.bridge_base_url.rstrip("/") + path
    request = urllib.request.Request(url, headers=bridge_headers(operacao), method="GET")
    with urllib.request.urlopen(request, timeout=4) as response:
        content = response.read().decode("utf-8") or "{}"
        return json.loads(content)


def bridge_logs_context(operacao, limit=20):
    if operacao is None:
        return []
    return list((operacao.metadados or {}).get("bridge_logs") or [])[:limit]


def bridge_status_summary(operacao):
    metadados = (operacao.metadados or {}) if operacao else {}
    return {
        "ultimo_comando_recebido": metadados.get("ultimo_comando_recebido"),
        "ultimo_comando_executado": metadados.get("ultimo_comando_executado"),
        "hora_ultima_confirmacao": metadados.get("hora_ultima_confirmacao"),
        "ultimo_heartbeat_recebido": metadados.get("ultimo_heartbeat_recebido"),
        "ultimo_estado_bridge": getattr(operacao, "bridge_ultimo_estado", ""),
        "ultimo_erro_bridge": getattr(operacao, "bridge_ultimo_erro", ""),
    }
