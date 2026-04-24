import json
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from geologia.bridge.sources import normalize_external_payload


def utc_iso():
    return datetime.now(UTC).isoformat()


class BridgeState:
    def __init__(
        self,
        host,
        port,
        equipamento="DJI Mini 4 Pro + DJI RC 2",
        ui_title="Bridge DJI RC 2",
        service_name="bridge_dji_rc2",
        source_mode="mock",
        source_description="Fonte simulada local",
        webhook_path="/webhook",
        webhook_token="",
    ):
        self.host = host
        self.port = port
        self.equipamento = equipamento
        self.ui_title = ui_title
        self.service_name = service_name
        self.source_mode = source_mode
        self.source_description = source_description
        self.webhook_path = webhook_path or "/webhook"
        self.webhook_token = webhook_token or ""
        self.started_at = time.time()
        self.lock = threading.Lock()
        self.telemetry = {
            "estado_bridge": "online",
            "estado_conexao": "pronto",
            "latitude": 40.211200,
            "longitude": -8.429800,
            "altitude_m": 0.0,
            "velocidade_ms": 0.0,
            "heading": 0.0,
            "bateria_percent": 96,
            "sinal_percent": 92,
            "gps_satellites": 16,
            "recording": False,
            "updated_at": utc_iso(),
        }

    @property
    def base_url(self):
        return f"http://{self.host}:{self.port}"

    def snapshot_url(self):
        return f"{self.base_url}/frame.svg"

    def live_url(self):
        return f"{self.base_url}/live"

    def webhook_url(self):
        return f"{self.base_url}{self.webhook_path}"

    def health_payload(self):
        with self.lock:
            payload = dict(self.telemetry)
        payload["stream_url"] = self.live_url()
        payload["snapshot_url"] = self.snapshot_url()
        payload["equipamento"] = self.equipamento
        payload["source_mode"] = self.source_mode
        payload["source_description"] = self.source_description
        return payload

    def update_from_query(self, query):
        mapping = {
            "lat": "latitude",
            "lon": "longitude",
            "alt": "altitude_m",
            "vel": "velocidade_ms",
            "heading": "heading",
            "bateria": "bateria_percent",
            "sinal": "sinal_percent",
            "gps": "gps_satellites",
        }
        with self.lock:
            for param, field in mapping.items():
                if param not in query or not query[param]:
                    continue
                raw = query[param][0]
                try:
                    if field in {"bateria_percent", "sinal_percent", "gps_satellites"}:
                        self.telemetry[field] = int(float(raw))
                    else:
                        self.telemetry[field] = float(raw)
                except ValueError:
                    continue

            if "estado" in query and query["estado"]:
                self.telemetry["estado_conexao"] = query["estado"][0]
            if "recording" in query and query["recording"]:
                self.telemetry["recording"] = query["recording"][0].lower() in {"1", "true", "yes", "on"}

            self.telemetry["updated_at"] = utc_iso()

    def update_from_payload(self, payload):
        if not isinstance(payload, dict):
            return
        payload = normalize_external_payload(payload)
        mapping = {
            "latitude": "latitude",
            "longitude": "longitude",
            "altitude_m": "altitude_m",
            "velocidade_ms": "velocidade_ms",
            "heading": "heading",
            "bateria_percent": "bateria_percent",
            "sinal_percent": "sinal_percent",
            "gps_satellites": "gps_satellites",
            "recording": "recording",
            "estado_conexao": "estado_conexao",
            "estado_bridge": "estado_bridge",
        }
        with self.lock:
            for source_key, target_key in mapping.items():
                if source_key not in payload:
                    continue
                self.telemetry[target_key] = payload[source_key]
            self.telemetry["updated_at"] = utc_iso()

    def tick(self):
        if self.source_mode == "webhook":
            with self.lock:
                self.telemetry["updated_at"] = utc_iso()
            return
        elapsed = time.time() - self.started_at
        phase = int(elapsed) % 240
        with self.lock:
            self.telemetry["heading"] = round((elapsed * 11) % 360, 1)
            self.telemetry["altitude_m"] = round(12 + (phase % 35), 1)
            self.telemetry["velocidade_ms"] = round(2.2 + ((phase % 9) * 0.17), 2)
            self.telemetry["latitude"] = round(40.211200 + ((phase % 25) * 0.000012), 6)
            self.telemetry["longitude"] = round(-8.429800 - ((phase % 25) * 0.000010), 6)
            self.telemetry["bateria_percent"] = max(24, 96 - int(elapsed // 45))
            self.telemetry["sinal_percent"] = 82 + (phase % 14)
            self.telemetry["gps_satellites"] = 14 + (phase % 5)
            self.telemetry["estado_bridge"] = "online"
            self.telemetry["estado_conexao"] = "em_voo" if phase > 20 else "pronto"
            self.telemetry["updated_at"] = utc_iso()

    def svg_snapshot(self):
        payload = self.health_payload()
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#082f49"/>
      <stop offset="55%" stop-color="#0f766e"/>
      <stop offset="100%" stop-color="#14532d"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="720" fill="url(#bg)"/>
  <rect x="38" y="38" width="1204" height="644" rx="20" fill="rgba(3,7,18,0.28)" stroke="rgba(255,255,255,0.18)"/>
  <text x="70" y="95" fill="white" font-size="30" font-family="Arial, sans-serif">{self.ui_title}</text>
  <text x="70" y="138" fill="#cbd5e1" font-size="21" font-family="Arial, sans-serif">Fonte: {payload["source_mode"]} | Estado: {payload["estado_conexao"]}</text>
  <text x="70" y="174" fill="#cbd5e1" font-size="21" font-family="Arial, sans-serif">Lat/Lon: {payload["latitude"]}, {payload["longitude"]} | Alt: {payload["altitude_m"]} m</text>
  <circle cx="640" cy="390" r="150" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.22)" stroke-width="2"/>
  <circle cx="640" cy="390" r="10" fill="#ffffff"/>
  <line x1="640" y1="390" x2="640" y2="210" stroke="white" stroke-width="3" stroke-dasharray="8 10"/>
  <line x1="490" y1="390" x2="790" y2="390" stroke="white" stroke-width="2" stroke-dasharray="5 10"/>
  <text x="70" y="640" fill="#e2e8f0" font-size="18" font-family="Arial, sans-serif">URL health: {self.base_url}/health</text>
  <text x="70" y="670" fill="#e2e8f0" font-size="18" font-family="Arial, sans-serif">Atualizado em: {payload["updated_at"]}</text>
</svg>""".encode("utf-8")

    def html_live_view(self):
        payload = self.health_payload()
        return f"""<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="3">
  <title>{self.ui_title}</title>
  <link rel="stylesheet" href="{self.base_url}/live.css">
</head>
<body>
  <div class="bridge-live-wrap">
    <p class="bridge-live-title">Live View da {self.ui_title}</p>
    <p class="bridge-live-muted">Base preparada para receber uma fonte DJI externa e empurrar dados para a plataforma.</p>
    <div class="bridge-live-grid">
      <div class="bridge-live-card"><img src="{self.snapshot_url()}" alt="Snapshot bridge" class="bridge-live-image"></div>
      <div class="bridge-live-card">
        <dl class="bridge-live-dl">
          <dt>Fonte</dt><dd>{payload["source_mode"]}</dd>
          <dt>Descrição</dt><dd>{payload["source_description"]}</dd>
          <dt>Estado</dt><dd>{payload["estado_conexao"]}</dd>
          <dt>Bateria</dt><dd>{payload["bateria_percent"]}%</dd>
          <dt>Sinal</dt><dd>{payload["sinal_percent"]}%</dd>
          <dt>Satélites</dt><dd>{payload["gps_satellites"]}</dd>
          <dt>Latitude</dt><dd>{payload["latitude"]}</dd>
          <dt>Longitude</dt><dd>{payload["longitude"]}</dd>
          <dt>Altitude</dt><dd>{payload["altitude_m"]} m</dd>
          <dt>Velocidade</dt><dd>{payload["velocidade_ms"]} m/s</dd>
          <dt>Heading</dt><dd>{payload["heading"]}°</dd>
          <dt>Atualizado</dt><dd>{payload["updated_at"]}</dd>
        </dl>
      </div>
    </div>
  </div>
</body>
</html>""".encode("utf-8")

    def live_css(self):
        css_path = Path(__file__).resolve().parents[2] / "static" / "css" / "geologia" / "bridge_runtime_live.css"
        try:
            return css_path.read_bytes()
        except OSError:
            return b""


class BridgeRuntimeServer:
    def __init__(self, state, logger, platform_log_url="", bridge_key=""):
        self.state = state
        self.logger = logger
        self.platform_log_url = platform_log_url
        self.bridge_key = bridge_key

    def build_handler(self):
        state = self.state
        logger = self.logger
        platform_log_url = self.platform_log_url
        bridge_key = self.bridge_key

        class BridgeHandler(BaseHTTPRequestHandler):
            def _write(self, status, payload, content_type="application/json; charset=utf-8"):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                if isinstance(payload, (dict, list)):
                    self.wfile.write(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
                else:
                    self.wfile.write(payload)

            def log_message(self, format, *args):
                message = "bridge: " + (format % args)
                logger(message)
                if platform_log_url and bridge_key:
                    send_bridge_log(platform_log_url, bridge_key, message)

            def do_GET(self):
                state.tick()
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                if query:
                    state.update_from_query(query)

                if parsed.path == "/health":
                    self._write(200, state.health_payload())
                    return
                if parsed.path == "/frame.svg":
                    self._write(200, state.svg_snapshot(), "image/svg+xml; charset=utf-8")
                    return
                if parsed.path == "/live":
                    self._write(200, state.html_live_view(), "text/html; charset=utf-8")
                    return
                if parsed.path == "/live.css":
                    self._write(200, state.live_css(), "text/css; charset=utf-8")
                    return
                if parsed.path == "/":
                    self._write(
                        200,
                        {
                            "ok": True,
                            "service": state.service_name,
                            "service_label": state.ui_title,
                            "health": f"{state.base_url}/health",
                            "live": f"{state.base_url}/live",
                            "frame": f"{state.base_url}/frame.svg",
                            "webhook": state.webhook_url(),
                            "source_mode": state.source_mode,
                        },
                    )
                    return
                self._write(404, {"ok": False, "erro": "Rota não encontrada."})

            def do_POST(self):
                state.tick()
                parsed = urlparse(self.path)
                if parsed.path == state.webhook_path:
                    if state.webhook_token:
                        header_token = self.headers.get("X-Webhook-Token", "")
                        query = parse_qs(parsed.query)
                        query_token = (query.get("token") or [""])[0]
                        if header_token != state.webhook_token and query_token != state.webhook_token:
                            self._write(403, {"ok": False, "erro": "Webhook não autorizado."})
                            return
                    content_length = int(self.headers.get("Content-Length", "0") or "0")
                    try:
                        payload = json.loads(self.rfile.read(content_length).decode("utf-8") or "{}")
                    except json.JSONDecodeError as exc:
                        self._write(400, {"ok": False, "erro": f"JSON inválido: {exc.msg}"})
                        return
                    state.update_from_payload(payload)
                    logger(f"Webhook de telemetria recebido em {state.webhook_path}")
                    if platform_log_url and bridge_key:
                        send_bridge_log(platform_log_url, bridge_key, f"Webhook de telemetria recebido em {state.webhook_path}", "sucesso")
                    self._write(200, {"ok": True, "estado": state.health_payload()})
                    return
                if parsed.path != "/simulate":
                    self._write(404, {"ok": False, "erro": "Rota não encontrada."})
                    return
                content_length = int(self.headers.get("Content-Length", "0") or "0")
                try:
                    payload = json.loads(self.rfile.read(content_length).decode("utf-8") or "{}")
                except json.JSONDecodeError as exc:
                    self._write(400, {"ok": False, "erro": f"JSON inválido: {exc.msg}"})
                    return
                state.update_from_query({k: [str(v)] for k, v in payload.items() if v is not None})
                self._write(200, {"ok": True, "estado": state.health_payload()})

        return BridgeHandler

    def serve_forever(self):
        server = ThreadingHTTPServer((self.state.host, self.state.port), self.build_handler())
        return server


def push_loop(state, platform_url, bridge_key, interval, logger):
    while True:
        try:
            state.tick()
            request = urllib.request.Request(
                platform_url,
                data=json.dumps(state.health_payload()).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Bridge-Key": bridge_key,
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=4) as response:
                response.read()
            logger(f"Heartbeat enviado para a plataforma em {platform_url}")
            send_bridge_log(platform_url.replace("/ingest/", "/log/"), bridge_key, f"Heartbeat enviado para a plataforma em {platform_url}", "sucesso")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            logger(f"Falha ao enviar heartbeat para a plataforma: {exc}")
            send_bridge_log(platform_url.replace("/ingest/", "/log/"), bridge_key, f"Falha ao enviar heartbeat para a plataforma: {exc}", "erro")
        time.sleep(interval)


def command_loop(state, platform_url, bridge_key, interval, logger):
    comandos_url = platform_url.replace("/ingest/", "/comandos/")
    while True:
        try:
            request = urllib.request.Request(
                comandos_url,
                headers={"X-Bridge-Key": bridge_key, "Accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8") or "{}")
            for comando in payload.get("comandos", []):
                process_command(state, platform_url, bridge_key, comando, logger)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            logger(f"Falha ao obter comandos pendentes: {exc}")
            send_bridge_log(platform_url.replace("/ingest/", "/log/"), bridge_key, f"Falha ao obter comandos pendentes: {exc}", "erro")
        time.sleep(interval)


def process_command(state, platform_url, bridge_key, comando, logger):
    tipo = comando.get("tipo_comando")
    message = f"Comando {tipo} processado pela bridge."
    with state.lock:
        if tipo == "goto":
            lat = comando.get("latitude_alvo")
            lon = comando.get("longitude_alvo")
            alt = comando.get("altitude_alvo_m")
            if lat is not None:
                state.telemetry["latitude"] = lat
            if lon is not None:
                state.telemetry["longitude"] = lon
            if alt is not None:
                state.telemetry["altitude_m"] = alt
            state.telemetry["estado_conexao"] = "em_missao"
        elif tipo == "capturar_foto":
            message = "Captura de foto registada pela bridge."
        elif tipo == "iniciar_video":
            state.telemetry["recording"] = True
            message = "Gravação iniciada pela bridge."
        elif tipo == "parar_video":
            state.telemetry["recording"] = False
            message = "Gravação terminada pela bridge."
        elif tipo == "rth":
            state.telemetry["estado_conexao"] = "em_missao"
            message = "Comando Return to Home recebido."
        elif tipo == "pairar":
            state.telemetry["velocidade_ms"] = 0.0
            message = "Drone colocado em pairar."
        state.telemetry["updated_at"] = utc_iso()

    confirm_url = platform_url.replace("/ingest/", f"/comandos/{comando['id']}/confirmar/")
    request = urllib.request.Request(
        confirm_url,
        data=json.dumps({"status": "executado", "mensagem": message}).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Bridge-Key": bridge_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=4) as response:
        response.read()
    logger(f"Comando {tipo} confirmado: {comando['id']}")
    send_bridge_log(platform_url.replace("/ingest/", "/log/"), bridge_key, f"Comando {tipo} confirmado: {comando['id']}", "sucesso")


def send_bridge_log(platform_log_url, bridge_key, message, level="info"):
    if not platform_log_url or not bridge_key or not message:
        return
    try:
        request = urllib.request.Request(
            platform_log_url,
            data=json.dumps({"mensagem": message, "tipo": level}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Bridge-Key": bridge_key},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            response.read()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return
