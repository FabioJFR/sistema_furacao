import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from geologia.bridge.sources import normalize_external_payload


class Command(BaseCommand):
    help = "Observa um ficheiro JSON externo e encaminha telemetria real para a bridge DJI em modo webhook."

    def add_arguments(self, parser):
        parser.add_argument("--input-file", required=True, help="Ficheiro JSON produzido por um processo externo.")
        parser.add_argument("--webhook-url", default="http://127.0.0.1:8787/webhook", help="URL do webhook da bridge.")
        parser.add_argument("--webhook-token", default="", help="Token opcional do webhook.")
        parser.add_argument("--poll-interval", type=float, default=1.0, help="Intervalo de verificação do ficheiro, em segundos.")
        parser.add_argument("--once", action="store_true", help="Lê uma vez e termina.")
        parser.add_argument("--estado", default="em_voo", help="Estado por defeito quando não vier no JSON.")
        parser.add_argument("--bridge-status", default="online", help="Estado da bridge por defeito quando não vier no JSON.")

    def handle(self, *args, **options):
        input_file = Path(options["input_file"]).expanduser()
        if not input_file.exists():
            raise CommandError(f"Ficheiro não encontrado: {input_file}")

        webhook_url = options["webhook_url"].strip()
        webhook_token = options["webhook_token"].strip()
        poll_interval = max(0.5, float(options["poll_interval"]))

        self.stdout.write(self.style.SUCCESS("Encaminhador de fonte DJI externa iniciado."))
        self.stdout.write(f"Origem:  {input_file}")
        self.stdout.write(f"Webhook: {webhook_url}")
        if webhook_token:
            self.stdout.write("Token webhook ativo.")

        last_signature = None
        try:
            while True:
                signature = self._build_signature(input_file)
                if signature != last_signature:
                    payload = self._load_payload(
                        input_file,
                        default_estado=options["estado"],
                        default_bridge_status=options["bridge_status"],
                    )
                    self._send_payload(webhook_url, webhook_token, payload)
                    self.stdout.write(
                        f"Telemetria encaminhada: lat={payload.get('latitude', '-')}, lon={payload.get('longitude', '-')}, alt={payload.get('altitude_m', '-')} m"
                    )
                    last_signature = signature
                    if options["once"]:
                        break
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Encaminhador interrompido pelo utilizador."))

    def _build_signature(self, input_file):
        stat = input_file.stat()
        return (stat.st_mtime_ns, stat.st_size)

    def _load_payload(self, input_file, default_estado, default_bridge_status):
        try:
            payload = json.loads(input_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON inválido em {input_file}: {exc.msg}") from exc

        if isinstance(payload, list):
            if not payload:
                raise CommandError(f"Lista vazia em {input_file}.")
            payload = payload[-1]
        if not isinstance(payload, dict):
            raise CommandError(f"O conteúdo de {input_file} tem de ser um objeto JSON ou uma lista de objetos.")

        return normalize_external_payload(
            payload,
            default_estado=default_estado,
            default_bridge_status=default_bridge_status,
        )

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
            raise CommandError(f"HTTP {exc.code} ao encaminhar telemetria: {body or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise CommandError(f"Falha de ligação ao webhook: {exc}") from exc
