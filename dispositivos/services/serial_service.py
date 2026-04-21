import binascii
import asyncio
import csv
import io
from typing import Optional

import serial
from serial.tools import list_ports

from dispositivos.models import Dispositivo, SessaoDispositivo, LeituraBrutaDispositivo

try:
    from bleak import BleakScanner
    from bleak import BleakClient
except Exception:  # pragma: no cover - fallback defensivo para ambientes sem bleak
    BleakScanner = None
    BleakClient = None


def _classificar_dispositivo_bluetooth(device) -> dict:
    """
    Classifica o dispositivo Bluetooth como genérico ou potencial aparelho de medidas.
    """
    name = (getattr(device, "name", None) or "").strip()
    address = (getattr(device, "address", None) or "").strip()
    details = str(getattr(device, "details", "") or "")[:200]
    manufacturer_data = getattr(device, "metadata", {}).get("manufacturer_data", {}) or {}
    uuids = getattr(device, "metadata", {}).get("uuids", []) or []
    rssi = getattr(device, "rssi", None)

    texto_base = " ".join(
        part.lower()
        for part in [name, address, details, " ".join(str(uuid) for uuid in uuids)]
        if part
    )

    palavras_medicao = [
        "mag",
        "cruiser",
        "survey",
        "probe",
        "sensor",
        "drill",
        "measure",
        "measurement",
        "sonda",
        "inclination",
        "azimuth",
    ]
    palavras_genericas = [
        "iphone",
        "ipad",
        "android",
        "samsung",
        "xiaomi",
        "huawei",
        "redmi",
        "macbook",
        "airpods",
        "watch",
        "phone",
        "telemovel",
        "telemóvel",
    ]

    score = 0
    reasons = []

    for palavra in palavras_medicao:
        if palavra in texto_base:
            score += 2
            reasons.append(f"contém '{palavra}'")

    if manufacturer_data:
        score += 1
        reasons.append("anuncia manufacturer data")

    if uuids:
        score += 1
        reasons.append("anuncia UUIDs BLE")

    if rssi is not None and rssi > -70:
        score += 1
        reasons.append("sinal próximo")

    is_generic_phone = any(palavra in texto_base for palavra in palavras_genericas)
    if is_generic_phone:
        score -= 2
        reasons.append("parece dispositivo pessoal genérico")

    is_candidate = score >= 2 and not is_generic_phone

    if is_candidate:
        label = "Possível aparelho de medidas"
        detail = "Este dispositivo anuncia sinais que merecem verificação."
    elif is_generic_phone:
        label = "Dispositivo genérico"
        detail = "Parece um telemóvel, auricular ou outro aparelho pessoal."
    else:
        label = "Bluetooth genérico"
        detail = "Foi detetado por Bluetooth, mas sem indícios claros de medição."

    return {
        "tipo_detectado": "candidato_medicao" if is_candidate else "generico",
        "tipo_label": label,
        "tipo_detalhe": detail,
        "motivos": reasons,
    }


def listar_portas_seriais() -> list[dict]:
    """
    Lista portas seriais disponíveis no sistema.
    """
    portas = []
    for p in list_ports.comports():
        portas.append({
            "device": p.device,
            "name": p.name,
            "description": p.description,
            "hwid": p.hwid,
            "manufacturer": getattr(p, "manufacturer", None),
            "product": getattr(p, "product", None),
            "serial_number": getattr(p, "serial_number", None),
        })
    return portas


def listar_dispositivos_bluetooth(timeout: float = 5.0) -> list[dict]:
    """
    Procura dispositivos Bluetooth/BLE visíveis no sistema.
    """
    if BleakScanner is None:
        raise RuntimeError("A biblioteca bleak não está disponível neste ambiente.")

    async def _scan():
        devices = await BleakScanner.discover(timeout=timeout)
        encontrados = []
        for device in devices:
            classificacao = _classificar_dispositivo_bluetooth(device)
            encontrados.append(
                {
                    "name": getattr(device, "name", None) or "Sem nome",
                    "address": getattr(device, "address", None) or "-",
                    "rssi": getattr(device, "rssi", None),
                    "details": str(getattr(device, "details", ""))[:200],
                    "tipo_detectado": classificacao["tipo_detectado"],
                    "tipo_label": classificacao["tipo_label"],
                    "tipo_detalhe": classificacao["tipo_detalhe"],
                    "motivos": classificacao["motivos"],
                    "tem_manufacturer_data": bool(
                        getattr(device, "metadata", {}).get("manufacturer_data", {})
                    ),
                    "tem_service_uuids": bool(
                        getattr(device, "metadata", {}).get("uuids", [])
                    ),
                }
            )
        return encontrados

    return asyncio.run(_scan())


def inspecionar_dispositivo_bluetooth(address: str, timeout: float = 8.0) -> dict:
    """
    Tenta ligar a um dispositivo BLE e recolher serviços/características visíveis.
    """
    if BleakScanner is None or BleakClient is None:
        raise RuntimeError("A biblioteca bleak não está disponível neste ambiente.")

    if not address:
        raise ValueError("É necessário indicar o endereço Bluetooth do dispositivo.")

    async def _inspect():
        devices = await BleakScanner.discover(timeout=4.0)
        target = next((device for device in devices if getattr(device, "address", None) == address), None)
        if target is None:
            raise RuntimeError("O dispositivo já não está visível para inspeção.")

        classification = _classificar_dispositivo_bluetooth(target)
        manufacturer_data = getattr(target, "metadata", {}).get("manufacturer_data", {}) or {}
        advertised_uuids = getattr(target, "metadata", {}).get("uuids", []) or []

        async with BleakClient(target, timeout=timeout) as client:
            services = []
            try:
                bleak_services = await client.get_services()
            except Exception:
                bleak_services = getattr(client, "services", None)

            if bleak_services:
                for service in bleak_services:
                    chars = []
                    for char in getattr(service, "characteristics", []) or []:
                        properties = list(getattr(char, "properties", []) or [])
                        chars.append(
                            {
                                "uuid": getattr(char, "uuid", None),
                                "description": getattr(char, "description", None) or "",
                                "properties": properties,
                            }
                        )
                    services.append(
                        {
                            "uuid": getattr(service, "uuid", None),
                            "description": getattr(service, "description", None) or "",
                            "characteristics": chars,
                        }
                    )

            return {
                "name": getattr(target, "name", None) or "Sem nome",
                "address": getattr(target, "address", None) or "-",
                "rssi": getattr(target, "rssi", None),
                "details": str(getattr(target, "details", ""))[:200],
                "tipo_detectado": classification["tipo_detectado"],
                "tipo_label": classification["tipo_label"],
                "tipo_detalhe": classification["tipo_detalhe"],
                "motivos": classification["motivos"],
                "connected": bool(getattr(client, "is_connected", False)),
                "manufacturer_data": {
                    str(key): str(value)[:120] for key, value in manufacturer_data.items()
                },
                "advertised_uuids": [str(uuid) for uuid in advertised_uuids],
                "services": services,
            }

    return asyncio.run(_inspect())


def ler_bytes_serial(
    porta: str,
    baudrate: int = 115200,
    timeout: float = 3.0,
    max_bytes: int = 4096,
) -> bytes:
    """
    Abre a porta serial e tenta ler bytes crus.
    """
    with serial.Serial(port=porta, baudrate=baudrate, timeout=timeout) as ser:
        data = ser.read(max_bytes)
        return data


def analisar_payload_bruto(raw_bytes: bytes) -> dict:
    """
    Normaliza um payload cru e tenta identificar conteúdo textual/CSV.
    """
    payload_hex = binascii.hexlify(raw_bytes).decode("ascii") if raw_bytes else ""
    payload_texto = raw_bytes.decode("utf-8", errors="replace") if raw_bytes else ""
    parece_csv = False
    csv_preview = []

    if payload_texto and "," in payload_texto and "\n" in payload_texto:
        try:
            sample = io.StringIO(payload_texto.strip())
            reader = csv.reader(sample)
            csv_preview = [row for _, row in zip(range(5), reader)]
            parece_csv = bool(csv_preview)
        except Exception:
            csv_preview = []

    return {
        "payload_texto": payload_texto,
        "payload_hex": payload_hex,
        "total_bytes": len(raw_bytes),
        "parece_csv": parece_csv,
        "csv_preview": csv_preview,
    }


def capturar_preview_serial_da_porta(
    porta: str,
    baudrate: int = 115200,
    max_bytes: int = 4096,
    timeout: float = 3.0,
) -> dict:
    """
    Lê bytes diretamente de uma porta serial detetada, sem exigir Dispositivo guardado.
    """
    if not porta:
        raise ValueError("É necessário indicar a porta serial.")

    raw_bytes = ler_bytes_serial(
        porta=porta,
        baudrate=baudrate,
        timeout=timeout,
        max_bytes=max_bytes,
    )
    payload = analisar_payload_bruto(raw_bytes)
    payload.update(
        {
            "porta": porta,
            "baudrate": baudrate,
            "timeout": timeout,
            "max_bytes": max_bytes,
        }
    )
    return payload


def guardar_leitura_bruta_da_sessao(
    sessao: SessaoDispositivo,
    raw_bytes: bytes,
    sequencia: int,
    origem: str = "usb",
    metadados: Optional[dict] = None,
) -> LeituraBrutaDispositivo:
    """
    Guarda um payload bruto recebido do dispositivo.
    """
    payload_hex = binascii.hexlify(raw_bytes).decode("ascii") if raw_bytes else ""
    payload_texto = ""

    if raw_bytes:
        payload_texto = raw_bytes.decode("utf-8", errors="replace")

    leitura = LeituraBrutaDispositivo.objects.create(
        sessao=sessao,
        empresa=sessao.empresa,
        sequencia=sequencia,
        origem=origem,
        payload_texto=payload_texto,
        payload_hex=payload_hex,
        payload_binario=raw_bytes if raw_bytes else None,
        metadados=metadados or {},
    )
    return leitura


def capturar_leitura_serial_para_sessao(
    sessao: SessaoDispositivo,
    max_bytes: int = 4096,
    timeout: float = 3.0,
) -> LeituraBrutaDispositivo:
    """
    Lê uma captura serial e guarda como leitura bruta.
    """
    dispositivo: Dispositivo = sessao.dispositivo

    if dispositivo.canal != "usb_serial":
        raise ValueError("O dispositivo da sessão não está configurado como USB / Serial.")

    if not dispositivo.porta:
        raise ValueError("O dispositivo não tem porta configurada.")

    raw_bytes = ler_bytes_serial(
        porta=dispositivo.porta,
        baudrate=dispositivo.baudrate,
        timeout=timeout,
        max_bytes=max_bytes,
    )

    ultima = (
        LeituraBrutaDispositivo.objects.filter(sessao=sessao)
        .order_by("-sequencia")
        .first()
    )
    proxima_sequencia = 1 if not ultima else ultima.sequencia + 1

    return guardar_leitura_bruta_da_sessao(
        sessao=sessao,
        raw_bytes=raw_bytes,
        sequencia=proxima_sequencia,
        origem="usb",
        metadados={
            "porta": dispositivo.porta,
            "baudrate": dispositivo.baudrate,
            "timeout": timeout,
            "max_bytes": max_bytes,
        },
    )


def capturar_preview_serial_do_dispositivo(
    dispositivo: Dispositivo,
    max_bytes: int = 4096,
    timeout: float = 3.0,
) -> dict:
    """
    Lê bytes do dispositivo sem persistir a captura.
    Útil para diagnóstico visual na UI.
    """
    if dispositivo.canal != "usb_serial":
        raise ValueError("O dispositivo selecionado não está configurado como USB / Serial.")

    if not dispositivo.porta:
        raise ValueError("O dispositivo não tem porta configurada.")

    raw_bytes = ler_bytes_serial(
        porta=dispositivo.porta,
        baudrate=dispositivo.baudrate,
        timeout=timeout,
        max_bytes=max_bytes,
    )

    payload = analisar_payload_bruto(raw_bytes)
    payload.update(
        {
            "porta": dispositivo.porta,
            "baudrate": dispositivo.baudrate,
            "timeout": timeout,
            "max_bytes": max_bytes,
        }
    )
    return payload
