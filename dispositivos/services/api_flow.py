def construir_resposta_operacao_api(*, resultado, payload_sucesso=None, mensagem_erro_padrao):
    if resultado["ok"]:
        data = payload_sucesso(resultado) if payload_sucesso else {}
        return {
            "ok": True,
            "payload": data,
            "status": 200,
            "eventos": resultado.get("eventos", []),
        }
    return {
        "ok": False,
        "payload": {},
        "status": resultado.get("status", 400),
        "eventos": resultado.get("eventos", []),
        "mensagem_erro": mensagem_erro_padrao,
    }


def construir_payload_dispositivo_guardado(resultado):
    dispositivo = resultado["dispositivo"]
    return {
        "eventos": resultado["eventos"],
        "dispositivo": {
            "id": str(dispositivo.pk),
            "nome": dispositivo.nome,
            "canal": dispositivo.canal,
            "identificador": (
                dispositivo.porta
                or dispositivo.mac_address
                or dispositivo.identificador_fisico
            ),
        },
    }


def construir_payload_escuta_dispositivo(resultado):
    payload = {
        "eventos": resultado["eventos"],
        "modo": resultado["modo"],
    }
    if resultado.get("leitura") is not None:
        payload["leitura"] = resultado["leitura"]
    if resultado.get("inspecao") is not None:
        payload["inspecao"] = resultado["inspecao"]
    return payload


def construir_http_response_operacao_api(
    *,
    resultado,
    payload_sucesso=None,
    mensagem_erro_padrao,
    json_ok_fn,
    json_erro_fn,
):
    api_resultado = construir_resposta_operacao_api(
        resultado=resultado,
        payload_sucesso=payload_sucesso,
        mensagem_erro_padrao=mensagem_erro_padrao,
    )
    if api_resultado["ok"]:
        return json_ok_fn(api_resultado["payload"], status=api_resultado["status"])
    return json_erro_fn(
        api_resultado["mensagem_erro"],
        status=api_resultado["status"],
        eventos=api_resultado["eventos"],
    )
