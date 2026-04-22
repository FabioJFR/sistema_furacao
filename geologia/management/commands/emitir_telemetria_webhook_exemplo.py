import json
import math
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime

from django.core.management.base import BaseCommand


def utc_iso():
    return datetime.now(UTC).isoformat()


class Command(BaseCommand):
    help = "Emite telemetria de exemplo para a bridge DJI em modo webhook."

    def add_arguments(self, parser):
        parser.add_argument("--webhook-url", default="http://127.0.0.1:8787/webhook", help="URL do webhook da bridge.")
        parser.add_argument("--webhook-token", default="", help="Token opcional do webhook.")
        parser.add_argument("--interval", type=float, default=2.0, help="Intervalo entre emissões, em segundos.")
        parser.add_argument("--once", action="store_true", help="Envia apenas uma amostra e termina.")
        parser.add_argument("--estado", default="em_voo", help="Estado de ligação a incluir no payload.")
        parser.add_argument("--bridge-status", default="online", help="Estado da bridge a incluir no payload.")
        parser.add_argument("--base-lat", type=float, default=40.211200, help="Latitude base da simulação.")
        parser.add_argument("--base-lon", type=float, default=-8.429800, help="Longitude base da simulação.")

    def handle(self, *args, **options):
        webhook_url = options["webhook_url"].strip()
        webhook_token = options["webhook_token"].strip()
        interval = max(0.5, float(options["interval"]))
        base_lat = float(options["base_lat"])
        base_lon = float(options["base_lon"])
        estado = options["estado"].strip() or "em_voo"
        bridge_status = options["bridge_status"].strip() or "online"

        self.stdout.write(self.style.SUCCESS("Emissor de telemetria webhook iniciado."))
        self.stdout.write(f"Webhook: {webhook_url}")
        if webhook_token:
            self.stdout.write("Token webhook ativo.")

        tick = 0
        try:
            while True:
                payload = self._build_payload(
                    tick=tick,
                    base_lat=base_lat,
                    base_lon=base_lon,
                    estado=estado,
                    bridge_status=bridge_status,
                )
                self._send_payload(webhook_url, webhook_token, payload)
                self.stdout.write(
                    f"Telemetria enviada: lat={payload['latitude']}, lon={payload['longitude']}, alt={payload['altitude_m']} m, heading={payload['heading']}°"
                )
                if options["once"]:
                    break
                tick += 1
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Emissor interrompido pelo utilizador."))

    def _build_payload(self, tick, base_lat, base_lon, estado, bridge_status):
        angle = tick / 3.0
        lat = base_lat + math.sin(angle) * 0.00018
        lon = base_lon + math.cos(angle) * 0.00016
        altitude = 22.0 + (math.sin(angle / 2.0) + 1.0) * 8.0
        velocidade = 2.2 + abs(math.cos(angle)) * 2.4
        heading = (tick * 17) % 360
        bateria = max(28, 97 - (tick // 18))
        sinal = 84 + (tick % 12)
        gps = 15 + (tick % 4)

        return {
            "estado_bridge": bridge_status,
            "estado_conexao": estado,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "altitude_m": round(altitude, 1),
            "velocidade_ms": round(velocidade, 2),
            "heading": round(heading, 1),
            "bateria_percent": int(bateria),
            "sinal_percent": int(min(99, sinal)),
            "gps_satellites": int(gps),
            "recording": tick % 9 >= 4,
            "updated_at": utc_iso(),
        }

    def _send_payload(self, webhook_url, webhook_token, payload):
        headers = {"Content-Type": "application/json"}
        if webhook_token:
            headers["X-Webhook-Token"] = webhook_token

        request = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=4) as response:
                response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code} ao enviar telemetria: {body or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Falha de ligação ao webhook: {exc}") from exc
