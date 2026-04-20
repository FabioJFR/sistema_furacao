from decimal import Decimal


def parse_magcruiser_payload(raw: str) -> dict:
    """
    Exemplo esperado:
    DEPTH=120.50;INC=-65.20;AZI=182.10;MAG=44.20;TEMP=23.50
    """
    partes = {}
    for item in raw.split(";"):
        if "=" not in item:
            continue
        chave, valor = item.split("=", 1)
        partes[chave.strip().lower()] = valor.strip()

    return {
        "profundidade": Decimal(partes["depth"]),
        "inclinacao": Decimal(partes["inc"]),
        "azimute": Decimal(partes["azi"]),
        "magnetismo": Decimal(partes["mag"]) if "mag" in partes else None,
        "temperatura": Decimal(partes["temp"]) if "temp" in partes else None,
        "payload_texto": raw,
    }