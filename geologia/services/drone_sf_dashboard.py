import json
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.utils import timezone

from geologia.forms import ComandoDroneSFOperacaoForm
from geologia.services.drone_sf_missoes import processar_missoes_programadas_drone_sf
from geologia.models import (
    ComandoDroneSFOperacao,
    ConfiguracaoDroneSF,
    DroneSF,
    ModuloDroneSF,
    OperacaoDroneSFTempoReal,
    SensorDroneSF,
)
from geologia.selectors.dashboard import obter_comandos_pendentes_ou_enviados_operacao_sf


def append_bridge_log_sf(operacao, mensagem, tipo="info"):
    if operacao is None or not mensagem:
        return
    metadados = dict(operacao.metadados or {})
    logs = list(metadados.get("bridge_logs") or [])
    logs.insert(
        0,
        {
            "mensagem": str(mensagem),
            "tipo": tipo,
            "timestamp": timezone.now().isoformat(),
        },
    )
    metadados["bridge_logs"] = logs[:40]
    operacao.metadados = metadados


def set_bridge_meta_sf(operacao, key, value):
    if operacao is None:
        return
    metadados = dict(operacao.metadados or {})
    metadados[key] = value
    operacao.metadados = metadados


def normalizar_estado_bridge_sf(operacao, payload):
    if not isinstance(payload, dict):
        return
    estado_bridge = payload.get("estado_bridge") or payload.get("bridge_status") or ""
    if estado_bridge:
        operacao.bridge_ultimo_estado = str(estado_bridge)[:120]
    operacao.live_view_url = payload.get("live_view_url") or payload.get("stream_url") or operacao.live_view_url
    operacao.frame_snapshot_url = payload.get("frame_snapshot_url") or payload.get("snapshot_url") or operacao.frame_snapshot_url
    operacao.latitude_atual = payload.get("latitude_atual", payload.get("latitude", operacao.latitude_atual))
    operacao.longitude_atual = payload.get("longitude_atual", payload.get("longitude", operacao.longitude_atual))
    operacao.altitude_atual_m = payload.get("altitude_atual_m", payload.get("altitude_m", operacao.altitude_atual_m))
    operacao.velocidade_atual_ms = payload.get("velocidade_atual_ms", payload.get("velocidade_ms", operacao.velocidade_atual_ms))
    operacao.heading_graus = payload.get("heading_graus", payload.get("heading", operacao.heading_graus))
    operacao.bateria_percent = payload.get("bateria_percent", operacao.bateria_percent)
    operacao.sinal_percent = payload.get("sinal_percent", operacao.sinal_percent)
    operacao.gravacao_ativa = bool(payload.get("gravacao_ativa", payload.get("recording", operacao.gravacao_ativa)))
    operacao.ultimo_heartbeat = timezone.now()
    operacao.bridge_ultimo_erro = ""

    estado = payload.get("estado_conexao")
    if estado in dict(OperacaoDroneSFTempoReal.ESTADO_CHOICES):
        operacao.estado = estado
    elif operacao.live_view_url or operacao.frame_snapshot_url:
        operacao.estado = "pronto"

    operacao.metadados = {
        **(operacao.metadados or {}),
        "bridge_payload_mais_recente": payload,
    }


def bridge_logs_context_sf(operacao, limit=20):
    if operacao is None:
        return []
    return list((operacao.metadados or {}).get("bridge_logs") or [])[:limit]


def bridge_status_summary_sf(operacao):
    metadados = (operacao.metadados or {}) if operacao else {}
    return {
        "ultimo_comando_recebido": metadados.get("ultimo_comando_recebido"),
        "ultimo_comando_executado": metadados.get("ultimo_comando_executado"),
        "hora_ultima_confirmacao": metadados.get("hora_ultima_confirmacao"),
        "ultimo_heartbeat_recebido": metadados.get("ultimo_heartbeat_recebido"),
        "ultimo_estado_bridge": getattr(operacao, "bridge_ultimo_estado", ""),
        "ultimo_erro_bridge": getattr(operacao, "bridge_ultimo_erro", ""),
    }


def motor_missoes_summary_sf(operacao):
    metadados = (operacao.metadados or {}) if operacao else {}
    return metadados.get("motor_missoes_programadas") or {}


def registar_execucao_manual_missao_sf(operacao, missao, comando):
    if operacao is None:
        return
    metadados = dict(operacao.metadados or {})
    resumo = dict(metadados.get("motor_missoes_programadas") or {})
    ultimas_missoes = list(resumo.get("ultimas_missoes_disparadas") or [])
    ultimos_comandos = list(resumo.get("ultimos_comandos_gerados") or [])

    timestamp = timezone.now().isoformat()
    ultimas_missoes.insert(
        0,
        {
            "nome": missao.nome,
            "origem": "Manual",
            "timestamp": timestamp,
        },
    )
    ultimos_comandos.insert(
        0,
        {
            "tipo": comando.get_tipo_comando_display(),
            "status": comando.get_status_display(),
            "origem": "Manual",
            "timestamp": timestamp,
        },
    )

    resumo["ultimas_missoes_disparadas"] = ultimas_missoes[:5]
    resumo["ultimos_comandos_gerados"] = ultimos_comandos[:5]
    metadados["motor_missoes_programadas"] = resumo
    operacao.metadados = metadados
    operacao.save(update_fields=["metadados", "atualizado_em"])


def criar_comando_drone_sf_from_form(*, form, operacao, utilizador):
    comando = form.save(commit=False)
    comando.criado_por = utilizador
    comando.payload = {
        "origem": "geologia_drone_sf",
        "alvo": {
            "latitude": comando.latitude_alvo,
            "longitude": comando.longitude_alvo,
            "altitude_m": comando.altitude_alvo_m,
        },
    }
    comando.save()
    return comando


def construir_form_comando_sf(*, request_post=None, operacao, empresa):
    if request_post is not None:
        return ComandoDroneSFOperacaoForm(
            request_post,
            prefix="comando_sf",
            operacao=operacao,
            empresa=empresa,
        )
    return ComandoDroneSFOperacaoForm(
        prefix="comando_sf",
        operacao=operacao,
        empresa=empresa,
        initial={"altitude_alvo_m": operacao.alvo_altitude_m or 35.0},
    )


def processar_comando_sf_create(*, request_post, operacao, empresa, utilizador):
    form = construir_form_comando_sf(
        request_post=request_post,
        operacao=operacao,
        empresa=empresa,
    )
    if form.is_valid():
        comando = criar_comando_drone_sf_from_form(
            form=form,
            operacao=operacao,
            utilizador=utilizador,
        )
        return {"ok": True, "form": form, "comando": comando}
    return {"ok": False, "form": form, "comando": None}


def executar_missao_programada_sf(*, operacao, missao, utilizador):
    comando = ComandoDroneSFOperacao.objects.create(
        operacao=operacao,
        empresa=missao.empresa,
        criado_por=utilizador,
        tipo_comando="goto",
        latitude_alvo=missao.latitude_alvo,
        longitude_alvo=missao.longitude_alvo,
        altitude_alvo_m=missao.altitude_alvo_m,
        payload={
            "origem": "missao_programada_drone_sf",
            "missao_programada_id": str(missao.id),
            "gravar_video": missao.gravar_video,
            "captar_foto": missao.captar_foto,
            "pairar_no_destino": missao.pairar_no_destino,
            "regressar_base": missao.regressar_base,
            "ativar_sensores": missao.ativar_sensores,
            "usar_live_view": missao.usar_live_view,
        },
    )
    registar_execucao_manual_missao_sf(operacao, missao, comando)
    missao.ultima_execucao_em = timezone.now()
    missao.save(update_fields=["ultima_execucao_em", "atualizado_em"])
    return comando


def atualizar_estado_missao_programada_sf(*, missao, ativa):
    missao.ativa = bool(ativa)
    missao.save(update_fields=["ativa", "atualizado_em"])
    return missao


def remover_missao_programada_sf(*, missao):
    nome_missao = missao.nome
    missao.delete()
    return nome_missao


def processar_toggle_missao_programada_sf(*, missao, ativa):
    atualizar_estado_missao_programada_sf(missao=missao, ativa=ativa)
    if ativa:
        return {"ok": True, "mensagem": "Repetição automática da missão ativada."}
    return {"ok": True, "mensagem": "Repetição automática da missão desativada."}


def processar_execucao_missao_programada_sf(*, operacao, missao, utilizador):
    executar_missao_programada_sf(operacao=operacao, missao=missao, utilizador=utilizador)
    return {
        "ok": True,
        "mensagem": "Missão programada enviada para execução imediata na fila do Drone S_F.",
    }


def processar_remocao_missao_programada_sf(*, missao):
    nome_missao = remover_missao_programada_sf(missao=missao)
    return {
        "ok": True,
        "mensagem": f"Missão programada '{nome_missao}' removida com sucesso.",
    }


def calcular_proxima_execucao_missao(missao):
    if not missao or not missao.ativa or not missao.hora_execucao:
        return None

    agora = timezone.localtime()
    base_local = timezone.localtime(timezone.now())
    proxima_data = base_local.date()

    if missao.tipo_frequencia == "semanal" and missao.dia_semana is not None:
        dias_ate_execucao = (missao.dia_semana - proxima_data.weekday()) % 7
        proxima_data = proxima_data + timedelta(days=dias_ate_execucao)

    proxima_naive = datetime.combine(proxima_data, missao.hora_execucao)
    proxima = timezone.make_aware(proxima_naive, timezone.get_current_timezone())

    if missao.tipo_frequencia == "diaria" and proxima <= agora:
        proxima += timedelta(days=1)
    elif missao.tipo_frequencia == "semanal" and proxima <= agora:
        proxima += timedelta(days=7)
    elif missao.tipo_frequencia == "pontual" and proxima <= agora:
        return None

    return proxima


def estado_agenda_missao(missao, proxima_execucao):
    if not missao.ativa:
        return {"label": "Parada", "tone": "slate"}
    if proxima_execucao is None:
        return {"label": "Sem próxima execução", "tone": "amber"}
    return {"label": "Agendada", "tone": "emerald"}


def construir_missoes_programadas_contexto(drone, limit=20):
    missoes_programadas = []
    for missao in drone.missoes_programadas.all()[:limit]:
        proxima_execucao = calcular_proxima_execucao_missao(missao)
        missoes_programadas.append(
            {
                "obj": missao,
                "proxima_execucao": proxima_execucao,
                "estado_agenda": estado_agenda_missao(missao, proxima_execucao),
            }
        )
    return missoes_programadas


def processar_acao_operacao_detail_sf(*, action, operacao_form, missao_programada_form, missao_edicao, empresa, utilizador):
    if action == "guardar_operacao":
        if operacao_form.is_valid():
            operacao_form.save()
            return {"handled": True, "ok": True, "message": "Operação em tempo real do Drone S_F atualizada."}
        return {"handled": True, "ok": False, "message": "Não foi possível atualizar a operação do Drone S_F."}

    if action == "guardar_missao_programada":
        if missao_programada_form.is_valid():
            missao_programada_form.save()
            if missao_edicao:
                return {"handled": True, "ok": True, "message": "Missão programada do Drone S_F atualizada com sucesso."}
            return {"handled": True, "ok": True, "message": "Missão programada do Drone S_F guardada com sucesso."}
        return {"handled": True, "ok": False, "message": "Não foi possível guardar a missão programada do Drone S_F."}

    if action == "processar_missoes_programadas":
        resumo = processar_missoes_programadas_drone_sf(empresa=empresa, utilizador=utilizador)
        return {
            "handled": True,
            "ok": True,
            "message": (
                f"Motor de missões S_F executado. "
                f"Executadas: {resumo['executadas']} · Ignoradas: {resumo['ignoradas']} · "
                f"Sem operação: {resumo['sem_operacao']}"
            ),
        }

    return {"handled": False}


def guardar_form_modelo_sf(form):
    if not form.is_valid():
        return None
    return form.save()


def processar_form_modelo_sf(*, form, mensagem_sucesso, mensagem_erro):
    objeto = guardar_form_modelo_sf(form)
    if objeto is None:
        return {
            "ok": False,
            "objeto": None,
            "mensagem": mensagem_erro,
        }
    return {
        "ok": True,
        "objeto": objeto,
        "mensagem": mensagem_sucesso,
    }


def serializar_estado_operacao_sf(operacao):
    return {
        "estado": operacao.estado,
        "estado_label": operacao.get_estado_display(),
        "ultimo_heartbeat": operacao.ultimo_heartbeat.isoformat() if operacao.ultimo_heartbeat else "",
        "bateria_percent": operacao.bateria_percent,
        "sinal_percent": operacao.sinal_percent,
        "latitude_atual": operacao.latitude_atual,
        "longitude_atual": operacao.longitude_atual,
        "altitude_atual_m": operacao.altitude_atual_m,
        "velocidade_atual_ms": operacao.velocidade_atual_ms,
        "heading_graus": operacao.heading_graus,
        "bridge_ativa": operacao.bridge_ativa,
        "bridge_nome": operacao.bridge_nome,
        "bridge_base_url": operacao.bridge_base_url,
        "bridge_ultimo_estado": operacao.bridge_ultimo_estado,
        "bridge_ultimo_erro": operacao.bridge_ultimo_erro,
        "bridge_source_mode": ((operacao.metadados or {}).get("bridge_payload_mais_recente") or {}).get("source_mode", ""),
        "bridge_logs": bridge_logs_context_sf(operacao),
        "bridge_status_summary": bridge_status_summary_sf(operacao),
        "motor_missoes_summary": motor_missoes_summary_sf(operacao),
        "live_view_url": operacao.live_view_url,
        "frame_snapshot_url": operacao.frame_snapshot_url,
    }


def parse_payload_json_request_sf(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}"), None
    except json.JSONDecodeError as exc:
        return None, JsonResponse({"ok": False, "erro": f"JSON inválido: {exc.msg}"}, status=400)


def resolver_operacao_bridge_sf(request, *, obter_operacao_por_bridge_key_fn, metodo="POST"):
    bridge_key = (request.headers.get("X-Bridge-Key") or "").strip()

    if not bridge_key:
        return {
            "ok": False,
            "operacao": None,
            "erro_response": JsonResponse(
                {
                    "ok": False,
                    "erro": "Bridge key em falta. Use o header X-Bridge-Key.",
                },
                status=403,
            ),
        }

    operacao = obter_operacao_por_bridge_key_fn(bridge_key)
    if operacao is None:
        return {"ok": False, "operacao": None, "erro_response": JsonResponse({"ok": False, "erro": "Bridge S_F não autorizada."}, status=403)}

    return {"ok": True, "operacao": operacao, "erro_response": None}


def serializar_comandos_bridge_sf(comandos_values):
    comandos = list(comandos_values)
    for comando in comandos:
        if hasattr(comando["criado_em"], "isoformat"):
            comando["criado_em"] = comando["criado_em"].isoformat()
    return comandos


def atualizar_status_comandos_enviados_sf(ids_pendentes):
    if ids_pendentes:
        ComandoDroneSFOperacao.objects.filter(id__in=ids_pendentes).update(status="enviado")


def processar_ingest_estado_bridge_sf(operacao, payload):
    normalizar_estado_bridge_sf(operacao, payload)
    append_bridge_log_sf(operacao, "Heartbeat recebido da bridge S_F.", "sucesso")
    set_bridge_meta_sf(operacao, "ultimo_heartbeat_recebido", timezone.now().isoformat())
    operacao.save()


def processar_comandos_pendentes_bridge_sf(operacao):
    comandos = serializar_comandos_bridge_sf(obter_comandos_pendentes_ou_enviados_operacao_sf(operacao))
    ids_pendentes = [item["id"] for item in comandos if item["status"] == "pendente"]
    atualizar_status_comandos_enviados_sf(ids_pendentes)
    if comandos:
        append_bridge_log_sf(operacao, f"Bridge S_F recolheu {len(comandos)} comando(s) pendente(s).", "info")
        operacao.save(update_fields=["metadados", "atualizado_em"])
    return comandos


def confirmar_comando_bridge_sf(*, comando, payload):
    novo_status = payload.get("status", "executado")
    if novo_status not in dict(ComandoDroneSFOperacao.STATUS_CHOICES):
        return JsonResponse({"ok": False, "erro": "Status inválido."}, status=400)

    comando.status = novo_status
    comando.resposta_execucao = payload.get("mensagem", "")
    comando.payload = {**(comando.payload or {}), "bridge_confirmacao": payload}
    comando.save(update_fields=["status", "resposta_execucao", "payload", "atualizado_em"])
    operacao = comando.operacao
    append_bridge_log_sf(
        operacao,
        f"Comando {comando.get_tipo_comando_display()} confirmado pela bridge S_F com estado {comando.get_status_display()}.",
        "sucesso" if novo_status == "executado" else "erro",
    )
    set_bridge_meta_sf(
        operacao,
        "ultimo_comando_executado",
        {
            "tipo": comando.get_tipo_comando_display(),
            "status": comando.get_status_display(),
            "timestamp": timezone.now().isoformat(),
        },
    )
    set_bridge_meta_sf(operacao, "hora_ultima_confirmacao", timezone.now().isoformat())
    operacao.save(update_fields=["metadados", "atualizado_em"])
    return None


def processar_log_event_bridge_sf(operacao, payload):
    mensagem = payload.get("mensagem") or payload.get("message") or ""
    tipo = payload.get("tipo") or payload.get("level") or "info"
    append_bridge_log_sf(operacao, mensagem, tipo)
    operacao.save(update_fields=["metadados", "atualizado_em"])


def criar_ou_obter_drone_sf_demo(empresa, bridge_key="bridge-drone-sf-local-001", bridge_url="http://127.0.0.1:8890"):
    drone, drone_created = DroneSF.objects.get_or_create(
        empresa=empresa,
        nome="Drone S_F Demo",
        defaults={
            "codigo": "SF-DEMO-001",
            "status": "teste",
            "frame_modelo": "Quadcopter S_F 650",
            "controlador_voo": "Pixhawk / ArduPilot",
            "firmware_voo": "ArduPilot",
            "protocolo_telemetria": "MAVLink",
            "companion_computer": "Raspberry Pi 5",
            "autonomia_alvo_min": 35,
            "payload_alvo_kg": 1.2,
            "peso_estimado_kg": 4.8,
            "tensao_sistema_v": 22.2,
            "observacoes": "Drone S_F demo criado automaticamente para testes da interface, sensores e bridge própria.",
        },
    )
    if not drone_created:
        if not drone.codigo:
            drone.codigo = "SF-DEMO-001"
        if not drone.frame_modelo:
            drone.frame_modelo = "Quadcopter S_F 650"
        if not drone.controlador_voo:
            drone.controlador_voo = "Pixhawk / ArduPilot"
        if not drone.firmware_voo:
            drone.firmware_voo = "ArduPilot"
        if not drone.protocolo_telemetria:
            drone.protocolo_telemetria = "MAVLink"
        if not drone.companion_computer:
            drone.companion_computer = "Raspberry Pi 5"
        drone.autonomia_alvo_min = drone.autonomia_alvo_min or 35
        drone.payload_alvo_kg = drone.payload_alvo_kg or 1.2
        drone.peso_estimado_kg = drone.peso_estimado_kg or 4.8
        if drone.tensao_sistema_v in (None, 0):
            drone.tensao_sistema_v = 22.2
        if not drone.observacoes:
            drone.observacoes = "Drone S_F demo criado automaticamente para testes da interface, sensores e bridge própria."
        drone.save()

    modulos = {}
    for payload in [
        {
            "nome": "Frame principal S_F",
            "tipo": "estrutura",
            "fabricante": "S_F Lab",
            "modelo": "SF-Frame-650",
            "firmware": "",
            "peso_kg": 1.35,
            "consumo_estimado_w": 0.0,
            "status": "ativo",
            "removivel": False,
            "observacoes": "Estrutura base do drone próprio.",
        },
        {
            "nome": "Controlador de voo",
            "tipo": "controlo_voo",
            "fabricante": "Pixhawk",
            "modelo": "Pixhawk 6C",
            "firmware": "ArduPilot",
            "peso_kg": 0.12,
            "consumo_estimado_w": 8.0,
            "status": "ativo",
            "removivel": True,
            "observacoes": "Camada de controlo de voo aberta para integração com a plataforma.",
        },
        {
            "nome": "Companion computer",
            "tipo": "computacao",
            "fabricante": "Raspberry Pi",
            "modelo": "Pi 5",
            "firmware": "Ubuntu / Python runtime",
            "peso_kg": 0.09,
            "consumo_estimado_w": 18.0,
            "status": "ativo",
            "removivel": True,
            "observacoes": "Execução de software embarcado, bridge e sensores.",
        },
        {
            "nome": "Módulo de comunicação",
            "tipo": "comunicacao",
            "fabricante": "S_F Link",
            "modelo": "SF-Link-01",
            "firmware": "Bridge runtime",
            "peso_kg": 0.08,
            "consumo_estimado_w": 7.5,
            "status": "ativo",
            "removivel": True,
            "observacoes": "Ligação entre o drone, a bridge S_F e a plataforma.",
        },
        {
            "nome": "Câmara principal",
            "tipo": "camera",
            "fabricante": "S_F Vision",
            "modelo": "RGB-4K-Gimbal",
            "firmware": "Cam stack 1.0",
            "peso_kg": 0.28,
            "consumo_estimado_w": 12.0,
            "status": "ativo",
            "removivel": True,
            "observacoes": "Captura visual para geologia, inspeção e fotogrametria.",
        },
    ]:
        modulo, _ = ModuloDroneSF.objects.get_or_create(
            drone=drone,
            nome=payload["nome"],
            defaults={**payload, "empresa": empresa},
        )
        modulos[payload["nome"]] = modulo

    for payload in [
        {
            "nome": "Sensor frontal de proximidade",
            "tipo": "proximidade",
            "modulo": modulos.get("Módulo de comunicação"),
            "fabricante": "S_F Sense",
            "modelo": "PROX-01",
            "interface_ligacao": "UART/I2C",
            "alcance_m": 25.0,
            "taxa_amostragem_hz": 15.0,
            "status": "ativo",
            "calibrado": True,
            "observacoes": "Evitar colisões e apoiar missões automáticas.",
        },
        {
            "nome": "Matriz de som ambiente",
            "tipo": "som",
            "modulo": modulos.get("Companion computer"),
            "fabricante": "S_F Sense",
            "modelo": "AUD-01",
            "interface_ligacao": "USB",
            "alcance_m": 40.0,
            "taxa_amostragem_hz": 44.1,
            "status": "ativo",
            "calibrado": True,
            "observacoes": "Captação de som e futura análise AI.",
        },
        {
            "nome": "Sensor RGB geológico",
            "tipo": "rgb",
            "modulo": modulos.get("Câmara principal"),
            "fabricante": "S_F Vision",
            "modelo": "RGB-4K-Sensor",
            "interface_ligacao": "CSI",
            "alcance_m": 120.0,
            "taxa_amostragem_hz": 30.0,
            "status": "ativo",
            "calibrado": True,
            "observacoes": "Captura principal para geologia e ortomosaico.",
        },
    ]:
        SensorDroneSF.objects.get_or_create(
            drone=drone,
            nome=payload["nome"],
            defaults={**payload, "empresa": empresa},
        )

    configuracao, _ = ConfiguracaoDroneSF.objects.get_or_create(
        drone=drone,
        defaults={
            "empresa": empresa,
            "telemetria_ativa": True,
            "video_ativo": True,
            "missao_automatica_ativa": True,
            "sensores_proximidade_ativos": True,
            "sensores_som_ativos": True,
            "software_embarcado_ativo": True,
            "endpoint_bridge": bridge_url,
            "api_key_bridge": bridge_key,
            "versao_software_embarcado": "sf-runtime-demo-1.0",
            "observacoes": "Configuração base do Drone S_F demo.",
        },
    )
    configuracao.telemetria_ativa = True
    configuracao.video_ativo = True
    configuracao.missao_automatica_ativa = True
    configuracao.sensores_proximidade_ativos = True
    configuracao.sensores_som_ativos = True
    configuracao.software_embarcado_ativo = True
    configuracao.endpoint_bridge = bridge_url
    configuracao.api_key_bridge = bridge_key
    configuracao.versao_software_embarcado = configuracao.versao_software_embarcado or "sf-runtime-demo-1.0"
    if not configuracao.observacoes:
        configuracao.observacoes = "Configuração base do Drone S_F demo."
    configuracao.save()

    operacao, _ = OperacaoDroneSFTempoReal.objects.get_or_create(
        drone=drone,
        defaults={
            "empresa": empresa,
            "estado": "pronto",
            "bridge_ativa": True,
            "bridge_nome": "Bridge S_F",
            "bridge_base_url": bridge_url,
            "bridge_api_key": bridge_key,
            "bridge_ultimo_estado": "ready",
            "latitude_atual": 40.210500,
            "longitude_atual": -8.430100,
            "altitude_atual_m": 0.0,
            "velocidade_atual_ms": 0.0,
            "heading_graus": 0.0,
            "bateria_percent": 95,
            "sinal_percent": 90,
            "gravacao_ativa": False,
            "alvo_latitude": 40.210500,
            "alvo_longitude": -8.430100,
            "alvo_altitude_m": 35.0,
            "observacoes": "Operação demo preparada para a bridge S_F.",
        },
    )
    operacao.estado = operacao.estado or "pronto"
    operacao.bridge_ativa = True
    operacao.bridge_nome = operacao.bridge_nome or "Bridge S_F"
    operacao.bridge_base_url = bridge_url
    operacao.bridge_api_key = bridge_key
    operacao.bridge_ultimo_estado = operacao.bridge_ultimo_estado or "ready"
    if operacao.latitude_atual is None:
        operacao.latitude_atual = 40.210500
    if operacao.longitude_atual is None:
        operacao.longitude_atual = -8.430100
    if operacao.altitude_atual_m is None:
        operacao.altitude_atual_m = 0.0
    if operacao.velocidade_atual_ms is None:
        operacao.velocidade_atual_ms = 0.0
    if operacao.heading_graus is None:
        operacao.heading_graus = 0.0
    if operacao.bateria_percent is None:
        operacao.bateria_percent = 95
    if operacao.sinal_percent is None:
        operacao.sinal_percent = 90
    if operacao.alvo_latitude is None:
        operacao.alvo_latitude = 40.210500
    if operacao.alvo_longitude is None:
        operacao.alvo_longitude = -8.430100
    operacao.alvo_altitude_m = operacao.alvo_altitude_m or 35.0
    if not operacao.observacoes:
        operacao.observacoes = "Operação demo preparada para a bridge S_F."
    operacao.save()

    ComandoDroneSFOperacao.objects.get_or_create(
        operacao=operacao,
        tipo_comando="goto",
        latitude_alvo=operacao.alvo_latitude,
        longitude_alvo=operacao.alvo_longitude,
        altitude_alvo_m=operacao.alvo_altitude_m,
        defaults={
            "empresa": empresa,
            "status": "pendente",
            "payload": {
                "origem": "seed_drone_sf_demo",
                "descricao": "Comando demo inicial para validar a fila do Drone S_F.",
            },
        },
    )
    return drone
