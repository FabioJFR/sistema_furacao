from dispositivos.services.serial_service import (
    capturar_preview_serial_da_porta,
    inspecionar_dispositivo_bluetooth,
    listar_dispositivos_bluetooth,
)


def processar_procura_dispositivos_bluetooth():
    try:
        dispositivos = listar_dispositivos_bluetooth()
        candidatos = sum(
            1 for dispositivo in dispositivos
            if dispositivo.get("tipo_detectado") == "candidato_medicao"
        )
        eventos = [
            {"tipo": "info", "mensagem": "A procurar dispositivos Bluetooth visíveis..."},
            {"tipo": "info", "mensagem": f"Foram encontrados {len(dispositivos)} dispositivos Bluetooth."},
        ]
        if candidatos:
            eventos.append(
                {
                    "tipo": "sucesso",
                    "mensagem": f"Foram identificados {candidatos} candidatos a aparelho de medidas.",
                }
            )
        else:
            eventos.append(
                {
                    "tipo": "info",
                    "mensagem": "Nenhum dispositivo foi identificado como candidato claro a aparelho de medidas.",
                }
            )
        return {
            "ok": True,
            "eventos": eventos,
            "dispositivos": dispositivos,
        }
    except Exception as exc:
        return {
            "ok": False,
            "eventos": [{"tipo": "erro", "mensagem": f"Erro ao procurar dispositivos Bluetooth: {exc}"}],
            "dispositivos": [],
            "status": 400,
        }


def processar_inspecao_bluetooth_detectado(*, address, name=""):
    if not address:
        return {
            "ok": False,
            "eventos": [
                {"tipo": "erro", "mensagem": "É necessário indicar o endereço Bluetooth para inspeção."}
            ],
            "status": 400,
        }

    eventos = [
        {"tipo": "info", "mensagem": f"A preparar inspeção Bluetooth para {name or address}."},
        {"tipo": "info", "mensagem": "A tentar ligar ao dispositivo para recolher serviços BLE..."},
    ]

    try:
        inspecao = inspecionar_dispositivo_bluetooth(address)
        total_services = len(inspecao.get("services") or [])
        total_characteristics = sum(
            len(service.get("characteristics") or [])
            for service in inspecao.get("services") or []
        )
        eventos.append(
            {
                "tipo": "sucesso",
                "mensagem": (
                    f"Inspeção concluída. Serviços: {total_services}. "
                    f"Características: {total_characteristics}."
                ),
            }
        )
        return {"ok": True, "eventos": eventos, "inspecao": inspecao}
    except Exception as exc:
        eventos.append(
            {
                "tipo": "erro",
                "mensagem": f"Não foi possível inspecionar o dispositivo Bluetooth: {exc}",
            }
        )
        return {"ok": False, "eventos": eventos, "status": 400}


def processar_escuta_dispositivo_detectado(*, canal, identificador, nome, baudrate=115200):
    if canal == "usb_serial":
        if not identificador:
            return {
                "ok": False,
                "eventos": [{"tipo": "erro", "mensagem": "É necessário indicar a porta USB/Serial."}],
                "status": 400,
            }
        eventos = [
            {"tipo": "info", "mensagem": f"A escutar a porta {identificador} do dispositivo {nome}."},
            {"tipo": "info", "mensagem": "A procurar bytes enviados pelo aparelho..."},
        ]
        try:
            leitura = capturar_preview_serial_da_porta(identificador, baudrate=baudrate)
            eventos.append(
                {
                    "tipo": "sucesso",
                    "mensagem": f"Foram recebidos {leitura['total_bytes']} bytes pela porta serial.",
                }
            )
            if leitura.get("parece_csv"):
                eventos.append(
                    {
                        "tipo": "sucesso",
                        "mensagem": "O conteúdo recebido parece estar em formato CSV.",
                    }
                )
            return {
                "ok": True,
                "eventos": eventos,
                "leitura": leitura,
                "modo": "usb_serial",
            }
        except Exception as exc:
            eventos.append({"tipo": "erro", "mensagem": f"Erro ao escutar a porta serial: {exc}"})
            return {"ok": False, "eventos": eventos, "status": 400}

    if canal == "bluetooth":
        if not identificador:
            return {
                "ok": False,
                "eventos": [{"tipo": "erro", "mensagem": "É necessário indicar o endereço Bluetooth."}],
                "status": 400,
            }
        eventos = [
            {"tipo": "info", "mensagem": f"A tentar escutar o dispositivo Bluetooth {nome}."},
            {"tipo": "info", "mensagem": "A recolher serviços e características BLE disponíveis..."},
        ]
        try:
            inspecao = inspecionar_dispositivo_bluetooth(identificador)
            total_services = len(inspecao.get("services") or [])
            eventos.append(
                {
                    "tipo": "sucesso",
                    "mensagem": f"Foram encontrados {total_services} serviços BLE durante a escuta.",
                }
            )
            eventos.append(
                {
                    "tipo": "info",
                    "mensagem": "A escuta Bluetooth genérica mostra metadados e serviços; streaming contínuo depende do protocolo do aparelho.",
                }
            )
            return {
                "ok": True,
                "eventos": eventos,
                "inspecao": inspecao,
                "modo": "bluetooth",
            }
        except Exception as exc:
            eventos.append({"tipo": "erro", "mensagem": f"Erro ao escutar Bluetooth: {exc}"})
            return {"ok": False, "eventos": eventos, "status": 400}

    return {
        "ok": False,
        "eventos": [{"tipo": "erro", "mensagem": "Canal não suportado para escuta."}],
        "status": 400,
    }
