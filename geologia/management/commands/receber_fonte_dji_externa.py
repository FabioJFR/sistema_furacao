import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from django.core.management.base import BaseCommand

from geologia.bridge.sources import normalize_external_payload


class Command(BaseCommand):
    help = "Arranca um recetor HTTP local para receber telemetria externa DJI e gravar num ficheiro JSON."

    def add_arguments(self, parser):
        parser.add_argument("--host", default="127.0.0.1", help="Host local do recetor.")
        parser.add_argument("--port", type=int, default=8791, help="Porta local do recetor.")
        parser.add_argument("--path", default="/ingest", help="Path HTTP para ingestão.")
        parser.add_argument("--output-file", default="/tmp/dji_telemetria.json", help="Ficheiro JSON de saída.")
        parser.add_argument("--token", default="", help="Token opcional para proteger a ingestão.")
        parser.add_argument("--estado", default="em_voo", help="Estado por defeito quando não vier no payload.")
        parser.add_argument("--bridge-status", default="online", help="Estado da bridge por defeito quando não vier no payload.")

    def handle(self, *args, **options):
        host = options["host"].strip() or "127.0.0.1"
        port = int(options["port"])
        ingest_path = (options["path"].strip() or "/ingest")
        if not ingest_path.startswith("/"):
            ingest_path = "/" + ingest_path
        output_file = Path(options["output_file"]).expanduser()
        token = options["token"].strip()
        default_estado = options["estado"].strip() or "em_voo"
        default_bridge_status = options["bridge_status"].strip() or "online"

        handler = self._build_handler(
            output_file=output_file,
            ingest_path=ingest_path,
            token=token,
            default_estado=default_estado,
            default_bridge_status=default_bridge_status,
        )
        server = ThreadingHTTPServer((host, port), handler)

        self.stdout.write(self.style.SUCCESS("Recetor de fonte DJI externa iniciado."))
        self.stdout.write(f"Ingestão: http://{host}:{port}{ingest_path}")
        self.stdout.write(f"Saída:    {output_file}")
        if token:
            self.stdout.write("Token HTTP configurado e obrigatório.")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Recetor interrompido pelo utilizador."))
        finally:
            server.server_close()

    def _build_handler(self, output_file, ingest_path, token, default_estado, default_bridge_status):
        logger = self.stdout.write

        class ReceiverHandler(BaseHTTPRequestHandler):
            def _write(self, status, payload):
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))

            def log_message(self, format, *args):
                logger("receiver: " + (format % args))

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/health":
                    self._write(
                        200,
                        {
                            "ok": True,
                            "service": "receber_fonte_dji_externa",
                            "ingest_path": ingest_path,
                            "output_file": str(output_file),
                        },
                    )
                    return
                self._write(404, {"ok": False, "erro": "Rota não encontrada."})

            def do_POST(self):
                parsed = urlparse(self.path)
                if parsed.path != ingest_path:
                    self._write(404, {"ok": False, "erro": "Rota não encontrada."})
                    return

                if token:
                    query = parse_qs(parsed.query)
                    query_token = (query.get("token") or [""])[0]
                    header_token = self.headers.get("X-Ingest-Token", "")
                    if query_token != token and header_token != token:
                        self._write(403, {"ok": False, "erro": "Token inválido."})
                        return

                content_length = int(self.headers.get("Content-Length", "0") or "0")
                try:
                    payload = json.loads(self.rfile.read(content_length).decode("utf-8") or "{}")
                except json.JSONDecodeError as exc:
                    self._write(400, {"ok": False, "erro": f"JSON inválido: {exc.msg}"})
                    return

                normalized = normalize_external_payload(
                    payload,
                    default_estado=default_estado,
                    default_bridge_status=default_bridge_status,
                )
                output_file.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
                logger(f"Telemetria externa recebida e gravada em {output_file}")
                self._write(
                    200,
                    {
                        "ok": True,
                        "output_file": str(output_file),
                        "payload": normalized,
                    },
                )

        return ReceiverHandler
