from dispositivos.models import Dispositivo, SessaoDispositivo


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


def criar_sessao_dispositivo(*, dispositivo, furo, empregado=None):
    return SessaoDispositivo.objects.create(
        dispositivo=dispositivo,
        empresa=dispositivo.empresa,
        empregado=empregado,
        furo=furo,
        status="criada",
    )
