import json
from datetime import datetime, timedelta
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from core.permissions import admin_required
from geologia.forms import (
    ComandoDroneSFOperacaoForm,
    ConfiguracaoDroneSFForm,
    DroneSFForm,
    MissaoProgramadaDroneSFForm,
    ModuloDroneSFForm,
    OperacaoDroneSFTempoRealForm,
    SensorDroneSFForm,
)
from geologia.models import LogGeologicoFuro, MissaoDroneFuro
from geologia.models import (
    ComandoDroneSFOperacao,
    ConfiguracaoDroneSF,
    DroneSF,
    MissaoProgramadaDroneSF,
    ModuloDroneSF,
    OperacaoDroneSFTempoReal,
    SensorDroneSF,
)
from geologia.services import processar_missoes_programadas_drone_sf
from projetos.models import Furo

from .common import filtrar_queryset_por_empresa, obter_empresa_admin_geologia


def _append_bridge_log_sf(operacao, mensagem, tipo="info"):
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


def _set_bridge_meta_sf(operacao, key, value):
    if operacao is None:
        return
    metadados = dict(operacao.metadados or {})
    metadados[key] = value
    operacao.metadados = metadados


def _normalizar_estado_bridge_sf(operacao, payload):
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


def _obter_operacao_sf_por_bridge_key(bridge_key):
    if not bridge_key:
        return None
    return OperacaoDroneSFTempoReal.objects.filter(bridge_api_key=bridge_key, bridge_ativa=True).first()


def _bridge_logs_context_sf(operacao, limit=20):
    if operacao is None:
        return []
    return list((operacao.metadados or {}).get("bridge_logs") or [])[:limit]


def _bridge_status_summary_sf(operacao):
    metadados = (operacao.metadados or {}) if operacao else {}
    return {
        "ultimo_comando_recebido": metadados.get("ultimo_comando_recebido"),
        "ultimo_comando_executado": metadados.get("ultimo_comando_executado"),
        "hora_ultima_confirmacao": metadados.get("hora_ultima_confirmacao"),
        "ultimo_heartbeat_recebido": metadados.get("ultimo_heartbeat_recebido"),
        "ultimo_estado_bridge": getattr(operacao, "bridge_ultimo_estado", ""),
        "ultimo_erro_bridge": getattr(operacao, "bridge_ultimo_erro", ""),
    }


def _motor_missoes_summary_sf(operacao):
    metadados = (operacao.metadados or {}) if operacao else {}
    return metadados.get("motor_missoes_programadas") or {}


def _registar_execucao_manual_missao_sf(operacao, missao, comando):
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


def _calcular_proxima_execucao_missao(missao):
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


def _estado_agenda_missao(missao, proxima_execucao):
    if not missao.ativa:
        return {"label": "Parada", "tone": "slate"}
    if proxima_execucao is None:
        return {"label": "Sem próxima execução", "tone": "amber"}
    return {"label": "Agendada", "tone": "emerald"}


def _criar_ou_obter_drone_sf_demo(empresa, bridge_key="bridge-drone-sf-local-001", bridge_url="http://127.0.0.1:8890"):
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


@login_required
@admin_required
def geologia_hub(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furos_qs = filtrar_queryset_por_empresa(
        Furo.objects.select_related("projeto").order_by("projeto__nome", "nome"),
        empresa=empresa,
    )
    logs_qs = filtrar_queryset_por_empresa(
        LogGeologicoFuro.objects.select_related("furo", "furo__projeto").order_by("-data_registo", "-criado_em"),
        empresa=empresa,
    )
    missoes_qs = filtrar_queryset_por_empresa(
        MissaoDroneFuro.objects.select_related("furo", "furo__projeto").order_by("-data_voo", "-criado_em"),
        empresa=empresa,
    )

    return render(
        request,
        "geologia/hub.html",
        {
            "contexto_geologia": contexto_geologia,
            "empresa_geologia": empresa,
            "furos": furos_qs[:12],
            "logs_recentes": logs_qs[:6],
            "missoes_recentes": missoes_qs[:6],
            "total_furos": furos_qs.count(),
            "total_logs": logs_qs.count(),
            "total_missoes": missoes_qs.count(),
        },
    )


@login_required
@admin_required
def drone_sf_hub(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furos_qs = filtrar_queryset_por_empresa(
        Furo.objects.select_related("projeto").order_by("projeto__nome", "nome"),
        empresa=empresa,
    )
    drones_qs = filtrar_queryset_por_empresa(
        DroneSF.objects.prefetch_related("modulos", "sensores").order_by("nome"),
        empresa=empresa,
    )
    missoes_qs = filtrar_queryset_por_empresa(
        MissaoDroneFuro.objects.select_related("furo", "furo__projeto").order_by("-data_voo", "-criado_em"),
        empresa=empresa,
    )

    knowledge_root = Path(__file__).resolve().parents[1].parent / "knowledge_base" / "drone"
    documentos_drone = []
    if knowledge_root.exists():
        for path in sorted(knowledge_root.iterdir()):
            if path.is_file():
                documentos_drone.append(
                    {
                        "nome": path.name,
                        "relativo": str(path.relative_to(knowledge_root.parent.parent)),
                    }
                )

    return render(
        request,
        "geologia/drone_sf_hub.html",
        {
            "contexto_geologia": contexto_geologia,
            "empresa_geologia": empresa,
            "total_furos": furos_qs.count(),
            "total_drones_sf": drones_qs.count(),
            "total_missoes": missoes_qs.count(),
            "furos": furos_qs[:10],
            "drones_sf": drones_qs[:8],
            "missoes_recentes": missoes_qs[:6],
            "documentos_drone": documentos_drone,
        },
    )


@login_required
@admin_required
@require_POST
def drone_sf_demo_create(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro
    if empresa is None:
        messages.error(request, "Seleciona uma empresa antes de criar o Drone S_F demo.")
        return redirect("geologia:drone_sf_hub")

    drone = _criar_ou_obter_drone_sf_demo(empresa=empresa)
    messages.success(request, "Drone S_F demo preparado com sucesso.")
    return redirect("geologia:drone_sf_detail", pk=drone.pk)


@login_required
@admin_required
def drone_sf_create(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    form = DroneSFForm(request.POST or None, empresa=empresa)
    if request.method == "POST":
        if form.is_valid():
            drone = form.save()
            messages.success(request, "Drone S_F criado com sucesso.")
            return redirect("geologia:drone_sf_detail", pk=drone.pk)
        messages.error(request, "Não foi possível criar o Drone S_F.")

    return render(
        request,
        "geologia/drone_sf_form.html",
        {
            "form": form,
            "empresa_geologia": empresa,
            "titulo": "Novo Drone S_F",
            "subtitulo": "Criar a base do drone próprio da plataforma.",
        },
    )


@login_required
@admin_required
def drone_sf_detail(request, pk):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = get_object_or_404(
        filtrar_queryset_por_empresa(DroneSF.objects.prefetch_related("modulos", "sensores"), empresa=empresa),
        pk=pk,
    )
    configuracao, _ = ConfiguracaoDroneSF.objects.get_or_create(
        drone=drone,
        defaults={"empresa": drone.empresa},
    )
    config_form = ConfiguracaoDroneSFForm(
        request.POST or None,
        instance=configuracao,
        drone=drone,
        empresa=drone.empresa,
    )
    if request.method == "POST":
        if config_form.is_valid():
            config_form.save()
            messages.success(request, "Configuração do Drone S_F atualizada.")
            return redirect("geologia:drone_sf_detail", pk=drone.pk)
        messages.error(request, "Não foi possível atualizar a configuração do Drone S_F.")

    return render(
        request,
        "geologia/drone_sf_detail.html",
        {
            "drone": drone,
            "configuracao": configuracao,
            "config_form": config_form,
            "empresa_geologia": empresa,
        },
    )


@login_required
@admin_required
def drone_sf_modulo_create(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = get_object_or_404(filtrar_queryset_por_empresa(DroneSF.objects.all(), empresa=empresa), pk=drone_id)
    form = ModuloDroneSFForm(request.POST or None, drone=drone, empresa=drone.empresa)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Módulo do Drone S_F criado com sucesso.")
            return redirect("geologia:drone_sf_detail", pk=drone.pk)
        messages.error(request, "Não foi possível criar o módulo do Drone S_F.")

    return render(
        request,
        "geologia/drone_sf_item_form.html",
        {
            "form": form,
            "empresa_geologia": empresa,
            "drone": drone,
            "titulo": f"Novo módulo - {drone.nome}",
            "subtitulo": "Componentes principais do drone, como estrutura, propulsão, computação e comunicação.",
            "botao_label": "Guardar módulo",
        },
    )


@login_required
@admin_required
def drone_sf_sensor_create(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = get_object_or_404(filtrar_queryset_por_empresa(DroneSF.objects.all(), empresa=empresa), pk=drone_id)
    form = SensorDroneSFForm(request.POST or None, drone=drone, empresa=drone.empresa)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Sensor do Drone S_F criado com sucesso.")
            return redirect("geologia:drone_sf_detail", pk=drone.pk)
        messages.error(request, "Não foi possível criar o sensor do Drone S_F.")

    return render(
        request,
        "geologia/drone_sf_item_form.html",
        {
            "form": form,
            "empresa_geologia": empresa,
            "drone": drone,
            "titulo": f"Novo sensor - {drone.nome}",
            "subtitulo": "Sensores de proximidade, som, RGB e outros módulos de leitura do Drone S_F.",
            "botao_label": "Guardar sensor",
        },
    )


@login_required
@admin_required
def drone_sf_operacao_detail(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = get_object_or_404(filtrar_queryset_por_empresa(DroneSF.objects.all(), empresa=empresa), pk=drone_id)
    missao_edicao = None
    missao_edicao_id = request.GET.get("editar_missao") or request.POST.get("missao_programada_id")
    if missao_edicao_id:
        missao_edicao = get_object_or_404(
            MissaoProgramadaDroneSF,
            drone=drone,
            empresa=drone.empresa,
            pk=missao_edicao_id,
        )
    operacao, _ = OperacaoDroneSFTempoReal.objects.get_or_create(
        drone=drone,
        defaults={"empresa": drone.empresa, "bridge_nome": "Bridge S_F"},
    )
    operacao_form = OperacaoDroneSFTempoRealForm(
        request.POST or None,
        instance=operacao,
        drone=drone,
        empresa=drone.empresa,
        prefix="operacao_sf",
    )
    comando_form = ComandoDroneSFOperacaoForm(
        prefix="comando_sf",
        operacao=operacao,
        empresa=drone.empresa,
        initial={"altitude_alvo_m": operacao.alvo_altitude_m or 35.0},
    )
    missao_programada_form = MissaoProgramadaDroneSFForm(
        request.POST or None,
        instance=missao_edicao,
        prefix="missao_sf",
        drone=drone,
        empresa=drone.empresa,
        initial={
            "nome": f"Missão diária {drone.nome}",
            "tipo_frequencia": "diaria",
            "hora_execucao": "08:00",
            "latitude_alvo": operacao.alvo_latitude,
            "longitude_alvo": operacao.alvo_longitude,
            "altitude_alvo_m": operacao.alvo_altitude_m or 35.0,
            "gravar_video": True,
            "captar_foto": False,
            "pairar_no_destino": False,
            "regressar_base": True,
            "ativar_sensores": True,
            "usar_live_view": True,
        },
    )
    if request.method == "POST" and request.POST.get("sf_action") == "guardar_operacao":
        if operacao_form.is_valid():
            operacao_form.save()
            messages.success(request, "Operação em tempo real do Drone S_F atualizada.")
            return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)
        messages.error(request, "Não foi possível atualizar a operação do Drone S_F.")
    elif request.method == "POST" and request.POST.get("sf_action") == "guardar_missao_programada":
        if missao_programada_form.is_valid():
            if missao_edicao:
                missao_programada_form.save()
                messages.success(request, "Missão programada do Drone S_F atualizada com sucesso.")
            else:
                missao_programada_form.save()
                messages.success(request, "Missão programada do Drone S_F guardada com sucesso.")
            return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)
        messages.error(request, "Não foi possível guardar a missão programada do Drone S_F.")
    elif request.method == "POST" and request.POST.get("sf_action") == "processar_missoes_programadas":
        resumo = processar_missoes_programadas_drone_sf(empresa=drone.empresa, utilizador=request.user)
        messages.success(
            request,
            (
                f"Motor de missões S_F executado. "
                f"Executadas: {resumo['executadas']} · Ignoradas: {resumo['ignoradas']} · "
                f"Sem operação: {resumo['sem_operacao']}"
            ),
        )
        return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)

    missoes_programadas = []
    for missao in drone.missoes_programadas.all()[:20]:
        proxima_execucao = _calcular_proxima_execucao_missao(missao)
        missoes_programadas.append(
            {
                "obj": missao,
                "proxima_execucao": proxima_execucao,
                "estado_agenda": _estado_agenda_missao(missao, proxima_execucao),
            }
        )

    return render(
        request,
        "geologia/drone_sf_operacao_detail.html",
        {
            "drone": drone,
            "operacao": operacao,
            "operacao_form": operacao_form,
            "comando_form": comando_form,
            "missao_programada_form": missao_programada_form,
            "missao_edicao": missao_edicao,
            "comandos_recentes": operacao.comandos.select_related("criado_por")[:10],
            "missoes_programadas": missoes_programadas,
            "bridge_logs": _bridge_logs_context_sf(operacao),
            "bridge_status_summary": _bridge_status_summary_sf(operacao),
            "motor_missoes_summary": _motor_missoes_summary_sf(operacao),
            "empresa_geologia": empresa,
        },
    )


@login_required
@admin_required
def drone_sf_comando_create(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = get_object_or_404(filtrar_queryset_por_empresa(DroneSF.objects.all(), empresa=empresa), pk=drone_id)
    operacao = get_object_or_404(OperacaoDroneSFTempoReal, drone=drone, empresa=drone.empresa)
    form = ComandoDroneSFOperacaoForm(request.POST or None, prefix="comando_sf", operacao=operacao, empresa=drone.empresa)
    if request.method == "POST":
        if form.is_valid():
            comando = form.save(commit=False)
            comando.criado_por = request.user
            comando.payload = {
                "origem": "geologia_drone_sf",
                "alvo": {
                    "latitude": comando.latitude_alvo,
                    "longitude": comando.longitude_alvo,
                    "altitude_m": comando.altitude_alvo_m,
                },
            }
            comando.save()
            messages.success(request, "Comando do Drone S_F colocado na fila.")
        else:
            messages.error(request, "Não foi possível criar o comando do Drone S_F.")
    return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)


@login_required
@admin_required
@require_POST
def drone_sf_missao_programada_toggle(request, drone_id, missao_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = get_object_or_404(filtrar_queryset_por_empresa(DroneSF.objects.all(), empresa=empresa), pk=drone_id)
    missao = get_object_or_404(MissaoProgramadaDroneSF, drone=drone, empresa=drone.empresa, pk=missao_id)

    novo_estado = request.POST.get("ativa") == "1"
    missao.ativa = novo_estado
    missao.save(update_fields=["ativa", "atualizado_em"])

    if novo_estado:
        messages.success(request, "Repetição automática da missão ativada.")
    else:
        messages.success(request, "Repetição automática da missão desativada.")
    return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)


@login_required
@admin_required
@require_POST
def drone_sf_missao_programada_executar(request, drone_id, missao_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = get_object_or_404(filtrar_queryset_por_empresa(DroneSF.objects.all(), empresa=empresa), pk=drone_id)
    operacao = get_object_or_404(OperacaoDroneSFTempoReal, drone=drone, empresa=drone.empresa)
    missao = get_object_or_404(MissaoProgramadaDroneSF, drone=drone, empresa=drone.empresa, pk=missao_id)

    comando = ComandoDroneSFOperacao.objects.create(
        operacao=operacao,
        empresa=drone.empresa,
        criado_por=request.user,
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
    _registar_execucao_manual_missao_sf(operacao, missao, comando)
    missao.ultima_execucao_em = timezone.now()
    missao.save(update_fields=["ultima_execucao_em", "atualizado_em"])
    messages.success(request, "Missão programada enviada para execução imediata na fila do Drone S_F.")
    return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)


@login_required
@admin_required
@require_POST
def drone_sf_missao_programada_delete(request, drone_id, missao_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = get_object_or_404(filtrar_queryset_por_empresa(DroneSF.objects.all(), empresa=empresa), pk=drone_id)
    missao = get_object_or_404(MissaoProgramadaDroneSF, drone=drone, empresa=drone.empresa, pk=missao_id)
    nome_missao = missao.nome
    missao.delete()
    messages.success(request, f"Missão programada '{nome_missao}' removida com sucesso.")
    return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)


@csrf_exempt
@require_POST
def api_drone_sf_bridge_ingest_estado(request):
    bridge_key = request.headers.get("X-Bridge-Key") or request.POST.get("bridge_key")
    if not bridge_key:
        return JsonResponse({"ok": False, "erro": "Bridge key em falta."}, status=403)

    operacao = _obter_operacao_sf_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge S_F não autorizada."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        return JsonResponse({"ok": False, "erro": f"JSON inválido: {exc.msg}"}, status=400)

    _normalizar_estado_bridge_sf(operacao, payload)
    _append_bridge_log_sf(operacao, "Heartbeat recebido da bridge S_F.", "sucesso")
    _set_bridge_meta_sf(operacao, "ultimo_heartbeat_recebido", timezone.now().isoformat())
    operacao.save()
    return JsonResponse(
        {
            "ok": True,
            "estado": {
                "estado": operacao.estado,
                "estado_label": operacao.get_estado_display(),
                "ultimo_heartbeat": operacao.ultimo_heartbeat.isoformat() if operacao.ultimo_heartbeat else "",
            },
        }
    )


@csrf_exempt
@require_GET
def api_drone_sf_bridge_comandos_pendentes(request):
    bridge_key = request.headers.get("X-Bridge-Key") or request.GET.get("bridge_key")
    operacao = _obter_operacao_sf_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge S_F não autorizada."}, status=403)

    comandos = list(
        operacao.comandos.filter(status__in=["pendente", "enviado"])
        .order_by("criado_em")
        .values(
            "id",
            "tipo_comando",
            "status",
            "latitude_alvo",
            "longitude_alvo",
            "altitude_alvo_m",
            "payload",
            "criado_em",
        )
    )
    for comando in comandos:
        if hasattr(comando["criado_em"], "isoformat"):
            comando["criado_em"] = comando["criado_em"].isoformat()

    ids_pendentes = [item["id"] for item in comandos if item["status"] == "pendente"]
    if ids_pendentes:
        ComandoDroneSFOperacao.objects.filter(id__in=ids_pendentes).update(status="enviado")
    if comandos:
        _append_bridge_log_sf(operacao, f"Bridge S_F recolheu {len(comandos)} comando(s) pendente(s).", "info")
        operacao.save(update_fields=["metadados", "atualizado_em"])
    return JsonResponse({"ok": True, "comandos": comandos})


@csrf_exempt
@require_POST
def api_drone_sf_bridge_confirmar_comando(request, comando_id):
    bridge_key = request.headers.get("X-Bridge-Key") or request.GET.get("bridge_key")
    operacao = _obter_operacao_sf_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge S_F não autorizada."}, status=403)

    comando = get_object_or_404(ComandoDroneSFOperacao, operacao=operacao, pk=comando_id)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        return JsonResponse({"ok": False, "erro": f"JSON inválido: {exc.msg}"}, status=400)

    novo_status = payload.get("status", "executado")
    if novo_status not in dict(ComandoDroneSFOperacao.STATUS_CHOICES):
        return JsonResponse({"ok": False, "erro": "Status inválido."}, status=400)

    comando.status = novo_status
    comando.resposta_execucao = payload.get("mensagem", "")
    comando.payload = {**(comando.payload or {}), "bridge_confirmacao": payload}
    comando.save(update_fields=["status", "resposta_execucao", "payload", "atualizado_em"])
    _append_bridge_log_sf(
        operacao,
        f"Comando {comando.get_tipo_comando_display()} confirmado pela bridge S_F com estado {comando.get_status_display()}.",
        "sucesso" if novo_status == "executado" else "erro",
    )
    _set_bridge_meta_sf(
        operacao,
        "ultimo_comando_executado",
        {
            "tipo": comando.get_tipo_comando_display(),
            "status": comando.get_status_display(),
            "timestamp": timezone.now().isoformat(),
        },
    )
    _set_bridge_meta_sf(operacao, "hora_ultima_confirmacao", timezone.now().isoformat())
    operacao.save(update_fields=["metadados", "atualizado_em"])
    return JsonResponse({"ok": True, "comando_id": str(comando.id), "status": comando.status})


@csrf_exempt
@require_POST
def api_drone_sf_bridge_log_event(request):
    bridge_key = request.headers.get("X-Bridge-Key") or request.POST.get("bridge_key")
    operacao = _obter_operacao_sf_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge S_F não autorizada."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        return JsonResponse({"ok": False, "erro": f"JSON inválido: {exc.msg}"}, status=400)

    mensagem = payload.get("mensagem") or payload.get("message") or ""
    tipo = payload.get("tipo") or payload.get("level") or "info"
    _append_bridge_log_sf(operacao, mensagem, tipo)
    operacao.save(update_fields=["metadados", "atualizado_em"])
    return JsonResponse({"ok": True})


@login_required
@admin_required
@require_GET
def api_drone_sf_estado(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return JsonResponse({"ok": False, "erro": "Sem permissões para consultar o estado do Drone S_F."}, status=403)

    drone = get_object_or_404(filtrar_queryset_por_empresa(DroneSF.objects.all(), empresa=empresa), pk=drone_id)
    operacao, _ = OperacaoDroneSFTempoReal.objects.get_or_create(
        drone=drone,
        defaults={"empresa": drone.empresa, "bridge_nome": "Bridge S_F"},
    )
    return JsonResponse(
        {
            "ok": True,
            "estado": {
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
                "bridge_logs": _bridge_logs_context_sf(operacao),
                "bridge_status_summary": _bridge_status_summary_sf(operacao),
                "motor_missoes_summary": _motor_missoes_summary_sf(operacao),
                "live_view_url": operacao.live_view_url,
                "frame_snapshot_url": operacao.frame_snapshot_url,
            },
        }
    )


@login_required
@admin_required
def furo_geologia_dashboard(request, furo_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furos_qs = filtrar_queryset_por_empresa(Furo.objects.select_related("projeto"), empresa=empresa)
    furo = get_object_or_404(furos_qs, pk=furo_id)
    logs = (
        furo.logs_geologicos.select_related("medicao", "missao_drone")
        .prefetch_related("anexos")
        .order_by("intervalo_de", "intervalo_ate", "-criado_em")
    )
    missoes = furo.missoes_drone_geologia.all().order_by("-data_voo", "-criado_em")

    return render(
        request,
        "geologia/furo_dashboard.html",
        {
            "furo": furo,
            "logs": logs,
            "missoes": missoes,
        },
    )
