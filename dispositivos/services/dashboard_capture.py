from dispositivos.models import SessaoDispositivo
from dispositivos.selectors.dashboard import obter_dispositivo_ativo, obter_furo
from dispositivos.services.serial_service import capturar_preview_serial_do_dispositivo


def criar_sessao_dispositivo(*, dispositivo, furo, empregado=None):
    return SessaoDispositivo.objects.create(
        dispositivo=dispositivo,
        empresa=dispositivo.empresa,
        empregado=empregado,
        furo=furo,
        status="criada",
    )


def processar_criacao_sessao_captura(
    *,
    empresa_id,
    empregado,
    dispositivo_id,
    furo_id,
):
    if not dispositivo_id or not furo_id:
        return {
            "ok": False,
            "erro": "Selecione um dispositivo e um furo para iniciar a sessão.",
            "status": 400,
        }

    dispositivo = obter_dispositivo_ativo(dispositivo_id, empresa_id=empresa_id)
    furo = obter_furo(furo_id, empresa_id=empresa_id)

    if dispositivo.empresa_id != furo.empresa_id:
        return {
            "ok": False,
            "erro": "O dispositivo e o furo têm de pertencer à mesma empresa.",
            "status": 400,
        }

    sessao = criar_sessao_dispositivo(dispositivo=dispositivo, furo=furo, empregado=empregado)
    return {"ok": True, "sessao": sessao}


def processar_teste_leitura_usb(*, dispositivo_id):
    if not dispositivo_id:
        return {
            "ok": False,
            "eventos": [
                {"tipo": "erro", "mensagem": "Selecione um dispositivo antes de testar a leitura."}
            ],
            "status": 400,
        }

    dispositivo = obter_dispositivo_ativo(dispositivo_id)

    eventos = [
        {"tipo": "info", "mensagem": f"Dispositivo selecionado: {dispositivo.nome}."},
        {"tipo": "info", "mensagem": "A validar configuração USB/Serial..."},
    ]

    try:
        eventos.append(
            {
                "tipo": "info",
                "mensagem": f"A ligar à porta {dispositivo.porta or '-'} com baudrate {dispositivo.baudrate}.",
            }
        )
        eventos.append(
            {
                "tipo": "info",
                "mensagem": "Ligado. A procurar dados enviados pelo aparelho...",
            }
        )

        leitura = capturar_preview_serial_do_dispositivo(dispositivo)
        eventos.append(
            {
                "tipo": "sucesso",
                "mensagem": f"Dados recebidos com sucesso. Total de bytes: {leitura['total_bytes']}.",
            }
        )
        return {
            "ok": True,
            "eventos": eventos,
            "leitura": leitura,
        }
    except Exception as exc:
        eventos.append(
            {
                "tipo": "erro",
                "mensagem": f"Erro durante a leitura: {exc}",
            }
        )
        return {
            "ok": False,
            "eventos": eventos,
            "status": 400,
        }
