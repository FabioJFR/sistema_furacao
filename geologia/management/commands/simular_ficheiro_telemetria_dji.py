import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand


def utc_iso():
    return datetime.now(UTC).isoformat()


class Command(BaseCommand):
    help = "Atualiza continuamente um ficheiro JSON de telemetria DJI para testes locais com a bridge."

    def add_arguments(self, parser):
        parser.add_argument("--output-file", default="/tmp/dji_telemetria.json", help="Ficheiro JSON de saída.")
        parser.add_argument("--interval", type=float, default=2.0, help="Intervalo entre atualizações, em segundos.")
        parser.add_argument("--base-lat", type=float, default=40.210500, help="Latitude base.")
        parser.add_argument("--base-lon", type=float, default=-8.430100, help="Longitude base.")
        parser.add_argument("--estado", default="em_voo", help="Estado de ligação a gravar.")
        parser.add_argument("--bridge-status", default="online", help="Estado da bridge a gravar.")
        parser.add_argument("--once", action="store_true", help="Grava só uma amostra e termina.")

    def handle(self, *args, **options):
        output_file = Path(options["output_file"]).expanduser()
        interval = max(0.5, float(options["interval"]))
        base_lat = float(options["base_lat"])
        base_lon = float(options["base_lon"])
        estado = options["estado"].strip() or "em_voo"
        bridge_status = options["bridge_status"].strip() or "online"

        self.stdout.write(self.style.SUCCESS("Simulador de ficheiro de telemetria DJI iniciado."))
        self.stdout.write(f"Destino: {output_file}")

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
                output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                self.stdout.write(
                    f"Ficheiro atualizado: lat={payload['latitude']}, lon={payload['longitude']}, alt={payload['altitude_m']} m, heading={payload['heading']}°"
                )
                if options["once"]:
                    break
                tick += 1
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Simulador interrompido pelo utilizador."))

    def _build_payload(self, tick, base_lat, base_lon, estado, bridge_status):
        angle = tick / 4.0
        lat = base_lat + math.sin(angle) * 0.00022
        lon = base_lon + math.cos(angle) * 0.00019
        altitude = 18.0 + (math.sin(angle / 2.0) + 1.0) * 10.0
        velocidade = 1.8 + abs(math.cos(angle)) * 3.1
        heading = (tick * 14) % 360
        bateria = max(25, 96 - (tick // 20))
        sinal = min(99, 83 + (tick % 14))
        gps = 15 + (tick % 5)

        return {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "altitude_m": round(altitude, 1),
            "velocidade_ms": round(velocidade, 2),
            "heading": round(heading, 1),
            "bateria_percent": int(bateria),
            "sinal_percent": int(sinal),
            "gps_satellites": int(gps),
            "recording": tick % 10 >= 4,
            "estado_conexao": estado,
            "estado_bridge": bridge_status,
            "updated_at": utc_iso(),
        }
