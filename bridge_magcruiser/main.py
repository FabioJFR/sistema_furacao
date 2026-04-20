import time
from driver import MagCruiserDriver
from sender import enviar_para_api
from config import PORTA_SERIAL, BAUDRATE


driver = MagCruiserDriver(PORTA_SERIAL, BAUDRATE)

print("Ligado ao MagCruiser...")

while True:
    try:
        raw = driver.read()

        if not raw:
            continue

        print(f"[RAW] {raw}")

        resposta = enviar_para_api({
            "payload": raw
        })

        print(f"[API] {resposta}")

    except Exception as e:
        print(f"[ERRO] {str(e)}")

    time.sleep(1)