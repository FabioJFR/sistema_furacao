import random
import time


def processar_teste_simulado():
    return {
        "ok": True,
        "eventos": [{"tipo": "sucesso", "mensagem": "Ligação simulada com sucesso."}],
        "status_simulado": "ok",
        "mensagem": "Ligação simulada com sucesso",
    }


def processar_captura_simulada():
    return {
        "ok": True,
        "eventos": [{"tipo": "sucesso", "mensagem": "Leitura simulada capturada com sucesso."}],
        "payload": {
            "depth": random.randint(10, 100),
            "inclination": round(random.uniform(-10, 10), 2),
            "azimuth": round(random.uniform(0, 360), 2),
            "timestamp": time.time(),
        },
    }
