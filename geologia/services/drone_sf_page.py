from geologia.services.drone_sf_dashboard import (
    parse_payload_json_request_sf,
    processar_acao_operacao_detail_sf,
    processar_comando_sf_create,
    resolver_operacao_bridge_sf,
)


def processar_post_operacao_detail_sf(
    *,
    request_method,
    action,
    operacao_form,
    missao_programada_form,
    missao_edicao,
    empresa,
    utilizador,
):
    if request_method != "POST":
        return {"handled": False, "ok": False, "message": "", "deve_redirecionar": False}
    resultado = processar_acao_operacao_detail_sf(
        action=action,
        operacao_form=operacao_form,
        missao_programada_form=missao_programada_form,
        missao_edicao=missao_edicao,
        empresa=empresa,
        utilizador=utilizador,
    )
    return {
        "handled": bool(resultado.get("handled")),
        "ok": bool(resultado.get("ok")),
        "message": resultado.get("message", ""),
        "deve_redirecionar": bool(resultado.get("handled")),
    }


def processar_post_comando_sf(
    *,
    request_method,
    request_post,
    operacao,
    empresa,
    utilizador,
):
    if request_method != "POST":
        return {"handled": False, "ok": False, "message": ""}
    resultado = processar_comando_sf_create(
        request_post=request_post,
        operacao=operacao,
        empresa=empresa,
        utilizador=utilizador,
    )
    return {
        "handled": True,
        "ok": bool(resultado["ok"]),
        "message": (
            "Comando do Drone S_F colocado na fila."
            if resultado["ok"]
            else "Não foi possível criar o comando do Drone S_F."
        ),
    }


def resolver_contexto_bridge_sf(
    *,
    request,
    obter_operacao_por_bridge_key_fn,
    metodo,
    requer_payload_json=False,
):
    acesso = resolver_operacao_bridge_sf(
        request,
        obter_operacao_por_bridge_key_fn=obter_operacao_por_bridge_key_fn,
        metodo=metodo,
    )
    if not acesso["ok"]:
        return {
            "ok": False,
            "operacao": None,
            "payload": None,
            "erro_response": acesso["erro_response"],
        }

    payload = None
    if requer_payload_json:
        payload, erro_response = parse_payload_json_request_sf(request)
        if erro_response is not None:
            return {
                "ok": False,
                "operacao": None,
                "payload": None,
                "erro_response": erro_response,
            }

    return {
        "ok": True,
        "operacao": acesso["operacao"],
        "payload": payload,
        "erro_response": None,
    }


def processar_acao_missao_programada_sf(
    *,
    acao,
    processar_toggle_fn=None,
    processar_execucao_fn=None,
    processar_remocao_fn=None,
    missao,
    operacao=None,
    utilizador=None,
    ativa=None,
):
    if acao == "toggle":
        resultado = processar_toggle_fn(missao=missao, ativa=ativa)
        return {"ok": True, "mensagem": resultado["mensagem"]}
    if acao == "executar":
        resultado = processar_execucao_fn(
            operacao=operacao,
            missao=missao,
            utilizador=utilizador,
        )
        return {"ok": True, "mensagem": resultado["mensagem"]}
    if acao == "remover":
        resultado = processar_remocao_fn(missao=missao)
        return {"ok": True, "mensagem": resultado["mensagem"]}
    return {"ok": False, "mensagem": "Ação inválida para missão programada."}


def processar_fluxo_form_modelo_sf(
    *,
    method,
    form,
    processar_form_modelo_sf_fn,
    mensagem_sucesso,
    mensagem_erro,
):
    if method != "POST":
        return {"handled": False, "ok": False, "mensagem": ""}

    resultado = processar_form_modelo_sf_fn(
        form=form,
        mensagem_sucesso=mensagem_sucesso,
        mensagem_erro=mensagem_erro,
    )
    return {
        "handled": True,
        "ok": bool(resultado.get("ok")),
        "mensagem": resultado.get("mensagem", ""),
        "objeto": resultado.get("objeto"),
    }
