import threading

from django.core.management.base import BaseCommand

from geologia.bridge.config import BridgeRuntimeConfig, load_bridge_runtime_config
from geologia.bridge.runtime import BridgeRuntimeServer, BridgeState, command_loop, push_loop


class Command(BaseCommand):
    help = "Arranca uma bridge local para DJI RC 2, com /health, /live, /frame.svg, heartbeat e consumo de comandos da plataforma."

    def add_arguments(self, parser):
        parser.add_argument("--config", default="", help="Ficheiro JSON de configuração da bridge.")
        parser.add_argument("--host", default="", help="Override do host local da bridge.")
        parser.add_argument("--port", type=int, default=0, help="Override da porta local da bridge.")
        parser.add_argument("--platform-url", default="", help="Override do endpoint de ingestão da plataforma.")
        parser.add_argument("--bridge-key", default="", help="Override da chave da bridge.")
        parser.add_argument("--push-interval", type=int, default=0, help="Override do intervalo, em segundos, para enviar heartbeat.")

    def handle(self, *args, **options):
        config = load_bridge_runtime_config(options["config"] or None)
        config = self._apply_overrides(config, options)

        state = BridgeState(
            host=config.host,
            port=config.port,
            equipamento=config.equipment_name,
            ui_title=config.ui_title,
            service_name=config.service_name,
            source_mode=config.source_mode,
            source_description=config.source_description,
            webhook_path=config.webhook_path,
            webhook_token=config.webhook_token,
        )
        server = BridgeRuntimeServer(
            state,
            self.stdout.write,
            platform_log_url=config.platform_ingest_url.replace("/ingest/", "/log/") if config.platform_ingest_url else "",
            bridge_key=config.bridge_key,
        ).serve_forever()

        if config.platform_ingest_url and config.bridge_key:
            threading.Thread(
                target=push_loop,
                args=(state, config.platform_ingest_url, config.bridge_key, config.push_interval, self.stdout.write),
                daemon=True,
            ).start()
            threading.Thread(
                target=command_loop,
                args=(state, config.platform_ingest_url, config.bridge_key, max(5, config.push_interval), self.stdout.write),
                daemon=True,
            ).start()

        self.stdout.write(self.style.SUCCESS("Bridge DJI RC 2 iniciada."))
        self.stdout.write(f"Health: {state.base_url}/health")
        self.stdout.write(f"Live:   {state.base_url}/live")
        self.stdout.write(f"Frame:  {state.base_url}/frame.svg")
        self.stdout.write(f"Webhook:{state.webhook_url()}")
        self.stdout.write(f"Fonte:  {config.source_mode} - {config.source_description}")
        if config.platform_ingest_url:
            self.stdout.write(f"Push plataforma: {config.platform_ingest_url}")
        if config.webhook_token:
            self.stdout.write("Webhook token configurado e obrigatório.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Bridge interrompida pelo utilizador."))
        finally:
            server.server_close()

    def _apply_overrides(self, config: BridgeRuntimeConfig, options):
        return BridgeRuntimeConfig(
            host=options["host"] or config.host,
            port=options["port"] or config.port,
            platform_ingest_url=(options["platform_url"] or config.platform_ingest_url).strip(),
            bridge_key=(options["bridge_key"] or config.bridge_key).strip(),
            push_interval=max(3, options["push_interval"] or config.push_interval),
            equipment_name=config.equipment_name,
            ui_title=config.ui_title,
            service_name=config.service_name,
            source_mode=config.source_mode,
            source_description=config.source_description,
            webhook_path=config.webhook_path,
            webhook_token=config.webhook_token,
        )
