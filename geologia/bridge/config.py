import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BridgeRuntimeConfig:
    host: str = "127.0.0.1"
    port: int = 8787
    platform_ingest_url: str = ""
    bridge_key: str = ""
    push_interval: int = 8
    equipment_name: str = "DJI Mini 4 Pro + DJI RC 2"
    ui_title: str = "Bridge DJI RC 2"
    service_name: str = "bridge_dji_rc2"
    source_mode: str = "mock"
    source_description: str = "Fonte simulada local"
    webhook_path: str = "/webhook"
    webhook_token: str = ""


def load_bridge_runtime_config(path: str | None = None) -> BridgeRuntimeConfig:
    if not path:
        return BridgeRuntimeConfig()

    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return BridgeRuntimeConfig(
        host=data.get("host", "127.0.0.1"),
        port=int(data.get("port", 8787)),
        platform_ingest_url=data.get("platform_ingest_url", "").strip(),
        bridge_key=data.get("bridge_key", "").strip(),
        push_interval=max(3, int(data.get("push_interval", 8))),
        equipment_name=data.get("equipment_name", "DJI Mini 4 Pro + DJI RC 2"),
        ui_title=data.get("ui_title", "Bridge DJI RC 2"),
        service_name=data.get("service_name", "bridge_dji_rc2"),
        source_mode=data.get("source_mode", "mock"),
        source_description=data.get("source_description", "Fonte simulada local"),
        webhook_path=(data.get("webhook_path", "/webhook") or "/webhook").strip() or "/webhook",
        webhook_token=data.get("webhook_token", "").strip(),
    )
