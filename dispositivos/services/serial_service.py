import binascii
from typing import Optional

import serial
from serial.tools import list_ports

from dispositivos.models import Dispositivo, SessaoDispositivo, LeituraBrutaDispositivo


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