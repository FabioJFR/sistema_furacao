import json
import urllib.error

from django.http import JsonResponse
from django.utils import timezone

from geologia.models import DroneComandoOperacao
from geologia.selectors.drone import obter_comandos_pendentes_ou_enviados_operacao
from geologia.services.drone_bridge import (
    append_bridge_log,
    bridge_logs_context,
    bridge_status_summary,
    buscar_estado_bridge,
    normalizar_estado_bridge,
    set_bridge_meta,
)


def serializar_estado_curto_operacao(operacao):
    return {
        "estado_conexao": operacao.estado_conexao,
        "estado_label": operacao.get_estado_conexao_display(),
        "ultimo_heartbeat": operacao.ultimo_heartbeat.isoformat() if operacao.ultimo_heartbeat else "",
        "feed_disponivel": bool(operacao.live_view_url or operacao.frame_snapshot_url),
    }


def serializar_estado_operacao(operacao):
    return {
        **serializar_estado_curto_operacao(operacao),
        "bateria_percent": operacao.bateria_percent,
        "sinal_percent": operacao.sinal_percent,
        "satelites_gps": operacao.satelites_gps,
        "bridge_ativa": operacao.bridge_ativa,
        "bridge_nome": operacao.bridge_nome,
        "bridge_base_url": operacao.bridge_base_url,
        "bridge_ultimo_estado": operacao.bridge_ultimo_estado,
        "bridge_ultimo_erro": operacao.bridge_ultimo_erro,
        "bridge_ultima_sincronizacao": operacao.bridge_ultima_sincronizacao.isoformat() if operacao.bridge_ultima_sincronizacao else "",
        "bridge_source_mode": ((operacao.metadados or {}).get("bridge_payload_mais_recente") or {}).get("source_mode", ""),
        "bridge_logs": bridge_logs_context(operacao),
        "bridge_status_summary": bridge_status_summary(operacao),
    }


def criar_comando_drone_from_form(*, form, operacao, empresa, user):
    comando = form.save(commit=False)
    comando.operacao = operacao
    comando.empresa = empresa
    comando.criado_por = user
    comando.payload = {
        "origem": "geologia_drone_hub",
        "alvo": {
            "latitude": comando.latitude_alvo,
            "longitude": comando.longitude_alvo,
            "altitude_m": comando.altitude_alvo_m,
        },
    }
    append_bridge_log(operacao, f"Comando colocado na fila: {comando.get_tipo_comando_display()}.", "info")
    set_bridge_meta(
        operacao,
        "ultimo_comando_recebido",
        {
            "tipo": comando.get_tipo_comando_display(),
            "status": comando.get_status_display(),
            "timestamp": timezone.now().isoformat(),
        },
    )
    comando.save()
    if comando.tipo_comando == "goto":
        operacao.alvo_latitude = comando.latitude_alvo
        operacao.alvo_longitude = comando.longitude_alvo
        operacao.alvo_altitude_m = comando.altitude_alvo_m or operacao.alvo_altitude_m
        operacao.save(update_fields=["alvo_latitude", "alvo_longitude", "alvo_altitude_m", "metadados", "atualizado_em"])
    else:
        operacao.save(update_fields=["metadados", "atualizado_em"])
    return comando


def testar_ligacao_drone(operacao):
    eventos = [
        {"tipo": "info", "mensagem": f"A iniciar teste de ligação ao {operacao.equipamento}."},
        {"tipo": "info", "mensagem": "A verificar feed configurado, heartbeat e contexto operacional..."},
    ]

    if operacao.bridge_ativa and operacao.bridge_base_url:
        try:
            payload = buscar_estado_bridge(operacao)
            normalizar_estado_bridge(operacao, payload)
            append_bridge_log(operacao, f"Teste de ligação bem sucedido em {operacao.bridge_base_url}.", "sucesso")
            operacao.save()
            eventos.append({"tipo": "sucesso", "mensagem": f"Bridge respondeu com sucesso em {operacao.bridge_base_url}."})
            if operacao.live_view_url or operacao.frame_snapshot_url:
                eventos.append({"tipo": "sucesso", "mensagem": "A bridge forneceu feed de vídeo/snapshot para o drone."})
        except (ValueError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            operacao.estado_conexao = "erro"
            operacao.bridge_ultimo_erro = str(exc)
            operacao.ultimo_heartbeat = timezone.now()
            append_bridge_log(operacao, f"Falha no teste de ligação: {exc}", "erro")
            operacao.save(update_fields=["estado_conexao", "bridge_ultimo_erro", "ultimo_heartbeat", "atualizado_em"])
            eventos.append({"tipo": "erro", "mensagem": f"Falha ao contactar a bridge: {exc}"})
            return False, eventos, serializar_estado_curto_operacao(operacao)

    if operacao.live_view_url or operacao.frame_snapshot_url:
        operacao.estado_conexao = "pronto"
        eventos.append({"tipo": "sucesso", "mensagem": "Foi encontrado feed configurado para o drone."})
    elif operacao.ultimo_heartbeat:
        operacao.estado_conexao = "procurando"
        eventos.append({"tipo": "info", "mensagem": "Existe heartbeat recente, mas ainda não há feed configurado."})
    else:
        operacao.estado_conexao = "procurando"
        eventos.append({"tipo": "info", "mensagem": "Sem heartbeat nem feed. O sistema ficou em modo de procura."})

    operacao.ultimo_heartbeat = timezone.now()
    operacao.save(update_fields=["estado_conexao", "ultimo_heartbeat", "atualizado_em"])
    return True, eventos, serializar_estado_curto_operacao(operacao)


def colocar_drone_em_procura(operacao):
    operacao.estado_conexao = "procurando"
    operacao.ultimo_heartbeat = timezone.now()
    append_bridge_log(operacao, "Bridge colocada em modo de procura do drone.", "info")
    operacao.save(update_fields=["estado_conexao", "ultimo_heartbeat", "atualizado_em"])

    eventos = [
        {"tipo": "info", "mensagem": f"A procurar o {operacao.equipamento} na infraestrutura local..."},
        {"tipo": "info", "mensagem": "A aguardar feed, bridge ou heartbeat do drone."},
    ]
    if operacao.live_view_url or operacao.frame_snapshot_url:
        eventos.append({"tipo": "sucesso", "mensagem": "Já existe feed configurado. O drone pode ser validado a qualquer momento."})
    return eventos


def serializar_comandos_bridge(comandos_values):
    comandos = list(comandos_values)
    for comando in comandos:
        if hasattr(comando["criado_em"], "isoformat"):
            comando["criado_em"] = comando["criado_em"].isoformat()
    return comandos


def atualizar_status_comandos_enviados(ids_pendentes):
    if ids_pendentes:
        DroneComandoOperacao.objects.filter(id__in=ids_pendentes).update(status="enviado")


def confirmar_comando_bridge(*, comando, payload):
    novo_status = payload.get("status", "executado")
    if novo_status not in dict(DroneComandoOperacao.STATUS_CHOICES):
        return JsonResponse({"ok": False, "erro": "Status inválido."}, status=400)

    comando.status = novo_status
    comando.resposta_execucao = payload.get("mensagem", "")
    comando.payload = {
        **(comando.payload or {}),
        "bridge_confirmacao": payload,
    }
    comando.save(update_fields=["status", "resposta_execucao", "payload", "atualizado_em"])
    operacao = comando.operacao
    append_bridge_log(
        operacao,
        f"Comando {comando.get_tipo_comando_display()} confirmado pela bridge com estado {comando.get_status_display()}.",
        "sucesso" if novo_status == "executado" else "erro",
    )
    set_bridge_meta(
        operacao,
        "ultimo_comando_executado",
        {
            "tipo": comando.get_tipo_comando_display(),
            "status": comando.get_status_display(),
            "timestamp": timezone.now().isoformat(),
        },
    )
    set_bridge_meta(operacao, "hora_ultima_confirmacao", timezone.now().isoformat())
    operacao.save(update_fields=["metadados", "atualizado_em"])
    return None


def parse_payload_json_request(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}"), None
    except json.JSONDecodeError as exc:
        return None, JsonResponse({"ok": False, "erro": f"JSON inválido: {exc.msg}"}, status=400)


def processar_ingest_estado_bridge(operacao, payload):
    normalizar_estado_bridge(operacao, payload)
    append_bridge_log(operacao, "Heartbeat recebido da bridge.", "sucesso")
    set_bridge_meta(operacao, "ultimo_heartbeat_recebido", timezone.now().isoformat())
    operacao.save()


def processar_comandos_pendentes_bridge(operacao):
    comandos = serializar_comandos_bridge(obter_comandos_pendentes_ou_enviados_operacao(operacao))
    ids_pendentes = [item["id"] for item in comandos if item["status"] == "pendente"]
    atualizar_status_comandos_enviados(ids_pendentes)
    if comandos:
        append_bridge_log(operacao, f"Bridge recolheu {len(comandos)} comando(s) pendente(s).", "info")
        operacao.save(update_fields=["metadados", "atualizado_em"])
    return comandos


def processar_log_event_bridge(operacao, payload):
    mensagem = payload.get("mensagem") or payload.get("message") or ""
    tipo = payload.get("tipo") or payload.get("level") or "info"
    append_bridge_log(operacao, mensagem, tipo)
    operacao.save(update_fields=["metadados", "atualizado_em"])
