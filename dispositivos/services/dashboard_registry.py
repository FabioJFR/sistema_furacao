from dispositivos.models import Dispositivo


def guardar_dispositivo_detectado(*, empresa, canal, nome, identificador, descricao="", baudrate=115200):
    defaults = {
        "empresa": empresa,
        "nome": nome[:120],
        "tipo": "magcruiser",
        "canal": canal,
        "numero_serie": "",
        "identificador_fisico": identificador[:120],
        "ativo": True,
    }
    if canal == "usb_serial":
        defaults["porta"] = identificador[:120]
        defaults["baudrate"] = baudrate
        dispositivo, created = Dispositivo.objects.update_or_create(
            empresa=empresa,
            porta=identificador[:120],
            defaults=defaults,
        )
    else:
        defaults["mac_address"] = identificador[:120]
        dispositivo, created = Dispositivo.objects.update_or_create(
            empresa=empresa,
            mac_address=identificador[:120],
            defaults=defaults,
        )
    eventos = [
        {"tipo": "sucesso", "mensagem": f"Dispositivo {'criado' if created else 'atualizado'} com sucesso."},
        {"tipo": "info", "mensagem": f"Empresa associada: {empresa}."},
    ]
    if descricao:
        eventos.append({"tipo": "info", "mensagem": f"Descrição detetada: {descricao}."})
    return dispositivo, created, eventos


def validar_parametros_dispositivo_detectado(*, canal, identificador):
    if canal not in {"usb_serial", "bluetooth"}:
        return {
            "ok": False,
            "erro": "Canal do dispositivo não suportado para registo.",
            "status": 400,
        }
    if not identificador:
        return {
            "ok": False,
            "erro": "Falta o identificador físico do dispositivo encontrado.",
            "status": 400,
        }
    return {"ok": True}


def processar_registo_dispositivo_detectado(
    *,
    empresa,
    canal,
    nome,
    identificador,
    descricao="",
    baudrate=115200,
):
    validacao = validar_parametros_dispositivo_detectado(canal=canal, identificador=identificador)
    if not validacao["ok"]:
        return validacao

    dispositivo, created, eventos = guardar_dispositivo_detectado(
        empresa=empresa,
        canal=canal,
        nome=nome,
        identificador=identificador,
        descricao=descricao,
        baudrate=baudrate,
    )
    return {
        "ok": True,
        "dispositivo": dispositivo,
        "created": created,
        "eventos": eventos,
    }
