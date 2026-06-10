from datetime import date, datetime, time
from decimal import Decimal


def normalizar_json_chat(valor):
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {str(chave): normalizar_json_chat(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple, set)):
        return [normalizar_json_chat(item) for item in valor]
    return str(valor)
