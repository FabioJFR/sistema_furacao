import json
import urllib.error
import urllib.request

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from core.permissions import admin_required
from geologia.forms import (
    DroneComandoOperacaoForm,
    DroneOperacaoTempoRealForm,
    ImportarMissaoDroneForm,
    MissaoDroneFuroForm,
)
from geologia.models import DroneComandoOperacao, DroneOperacaoTempoReal, MissaoDroneFuro
from projetos.models import Furo

from .common import filtrar_queryset_por_empresa, obter_empresa_admin_geologia


def _append_bridge_log(operacao, mensagem, tipo="info"):
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


def _set_bridge_meta(operacao, key, value):
    if operacao is None:
        return
    metadados = dict(operacao.metadados or {})
    metadados[key] = value
    operacao.metadados = metadados


def _bridge_headers(operacao):
    headers = {"Accept": "application/json"}
    if operacao.bridge_api_key:
        headers["X-Bridge-Key"] = operacao.bridge_api_key
    return headers


def _normalizar_estado_bridge(operacao, payload):
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
    operacao.satelites_gps = payload.get("satelites_gps", payload.get("gps_satellites", operacao.satelites_gps))
    operacao.gravacao_ativa = bool(payload.get("gravacao_ativa", payload.get("recording", operacao.gravacao_ativa)))
    operacao.ultimo_heartbeat = timezone.now()
    operacao.bridge_ultima_sincronizacao = timezone.now()
    operacao.bridge_ultimo_erro = ""

    estado_conexao = payload.get("estado_conexao")
    if estado_conexao in dict(DroneOperacaoTempoReal.ESTADO_CONEXAO_CHOICES):
        operacao.estado_conexao = estado_conexao
    elif operacao.live_view_url or operacao.frame_snapshot_url:
        operacao.estado_conexao = "pronto"
    else:
        operacao.estado_conexao = "procurando"

    operacao.metadados = {
        **(operacao.metadados or {}),
        "bridge_payload_mais_recente": payload,
    }


def _buscar_estado_bridge(operacao, path="/health"):
    if not operacao.bridge_ativa or not operacao.bridge_base_url:
        raise ValueError("Bridge não configurada.")

    url = operacao.bridge_base_url.rstrip("/") + path
    request = urllib.request.Request(url, headers=_bridge_headers(operacao), method="GET")
    with urllib.request.urlopen(request, timeout=4) as response:
        content = response.read().decode("utf-8") or "{}"
        return json.loads(content)


def _obter_operacao_por_bridge_key(bridge_key):
    if not bridge_key:
        return None
    return DroneOperacaoTempoReal.objects.filter(bridge_api_key=bridge_key, bridge_ativa=True).first()


def _bridge_logs_context(operacao, limit=20):
    if operacao is None:
        return []
    return list((operacao.metadados or {}).get("bridge_logs") or [])[:limit]


def _bridge_status_summary(operacao):
    metadados = (operacao.metadados or {}) if operacao else {}
    return {
        "ultimo_comando_recebido": metadados.get("ultimo_comando_recebido"),
        "ultimo_comando_executado": metadados.get("ultimo_comando_executado"),
        "hora_ultima_confirmacao": metadados.get("hora_ultima_confirmacao"),
        "ultimo_heartbeat_recebido": metadados.get("ultimo_heartbeat_recebido"),
        "ultimo_estado_bridge": getattr(operacao, "bridge_ultimo_estado", ""),
        "ultimo_erro_bridge": getattr(operacao, "bridge_ultimo_erro", ""),
    }


@login_required
@admin_required
def drone_hub(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furos_qs = filtrar_queryset_por_empresa(
        Furo.objects.select_related("projeto").order_by("projeto__nome", "nome"),
        empresa=empresa,
    )
    missoes_qs = filtrar_queryset_por_empresa(
        MissaoDroneFuro.objects.select_related("furo", "furo__projeto").order_by("-data_voo", "-criado_em"),
        empresa=empresa,
    )
    furos = list(furos_qs[:12])
    missoes_recentes = list(missoes_qs[:8])
    operacao = None
    operacao_form = None
    comando_form = None
    comandos_recentes = []
    if empresa is not None:
        operacao, _ = DroneOperacaoTempoReal.objects.get_or_create(
            empresa=empresa,
            defaults={
                "nome_operacao": "Centro de controlo DJI Mini 4 Pro",
                "estado_conexao": "desligado",
                "alvo_altitude_m": 35.0,
            },
        )
        operacao_form = DroneOperacaoTempoRealForm(
            request.POST or None,
            instance=operacao,
            empresa=empresa,
            prefix="operacao",
        )
        comando_form = DroneComandoOperacaoForm(
            prefix="comando",
            initial={"altitude_alvo_m": operacao.alvo_altitude_m or 35.0},
            operacao=operacao,
            empresa=empresa,
        )
        comandos_recentes = operacao.comandos.select_related("criado_por")[:10]

    if request.method == "POST" and request.POST.get("drone_action") == "importar_missao":
        form = ImportarMissaoDroneForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            missao = form.save()
            messages.success(request, "Missao DJI importada com sucesso.")
            return redirect("geologia:missao_detail", pk=missao.pk)
        messages.error(request, "Nao foi possivel importar a missao DJI.")
    else:
        form = ImportarMissaoDroneForm(empresa=empresa)

    context = {
        "form": form,
        "contexto_geologia": contexto_geologia,
        "empresa_geologia": empresa,
        "operacao_form": operacao_form,
        "comando_form": comando_form,
        "operacao": operacao,
        "bridge_logs": _bridge_logs_context(operacao),
        "bridge_status_summary": _bridge_status_summary(operacao),
        "comandos_recentes": comandos_recentes,
        "furos": furos,
        "missoes_recentes": missoes_recentes,
        "total_furos": furos_qs.count(),
        "total_missoes": missoes_qs.count(),
        "total_importadas": missoes_qs.filter(status="importada").count(),
    }
    return render(request, "geologia/drone_hub.html", context)


@login_required
@admin_required
def drone_controle_update(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro
    if empresa is None:
        messages.error(request, "O controlo em tempo real do drone precisa de uma empresa selecionada.")
        return redirect("geologia:drone_hub")

    operacao = get_object_or_404(DroneOperacaoTempoReal, empresa=empresa)
    form = DroneOperacaoTempoRealForm(
        request.POST or None,
        instance=operacao,
        empresa=empresa,
        prefix="operacao",
    )
    if request.method == "POST" and form.is_valid():
        operacao = form.save(commit=False)
        operacao.ultimo_heartbeat = timezone.now()
        operacao.save()
        messages.success(request, "Centro de controlo do drone atualizado.")
    else:
        messages.error(request, "Nao foi possivel atualizar o centro de controlo do drone.")
    return redirect("geologia:drone_hub")


@login_required
@admin_required
def drone_comando_create(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro
    if empresa is None:
        messages.error(request, "Os comandos do drone precisam de uma empresa selecionada.")
        return redirect("geologia:drone_hub")

    operacao = get_object_or_404(DroneOperacaoTempoReal, empresa=empresa)
    form = DroneComandoOperacaoForm(request.POST or None, prefix="comando", operacao=operacao, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        comando = form.save(commit=False)
        comando.operacao = operacao
        comando.empresa = empresa
        comando.criado_por = request.user
        comando.payload = {
            "origem": "geologia_drone_hub",
            "alvo": {
                "latitude": comando.latitude_alvo,
                "longitude": comando.longitude_alvo,
                "altitude_m": comando.altitude_alvo_m,
            },
        }
        _append_bridge_log(operacao, f"Comando colocado na fila: {comando.get_tipo_comando_display()}.", "info")
        _set_bridge_meta(
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
        messages.success(request, "Comando colocado na fila do drone.")
    else:
        messages.error(request, "Nao foi possivel criar o comando do drone.")
    return redirect("geologia:drone_hub")


@login_required
@admin_required
@require_GET
def api_testar_ligacao_drone(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return JsonResponse({"ok": False, "eventos": [{"tipo": "erro", "mensagem": "Sem permissões para testar a ligação do drone."}]}, status=403)
    if empresa is None:
        return JsonResponse({"ok": False, "eventos": [{"tipo": "erro", "mensagem": "A vista global não permite testar a ligação a um drone específico."}]}, status=400)

    operacao = get_object_or_404(DroneOperacaoTempoReal, empresa=empresa)
    eventos = [
        {"tipo": "info", "mensagem": f"A iniciar teste de ligação ao {operacao.equipamento}."},
        {"tipo": "info", "mensagem": "A verificar feed configurado, heartbeat e contexto operacional..."},
    ]

    if operacao.bridge_ativa and operacao.bridge_base_url:
        try:
            payload = _buscar_estado_bridge(operacao)
            _normalizar_estado_bridge(operacao, payload)
            _append_bridge_log(operacao, f"Teste de ligação bem sucedido em {operacao.bridge_base_url}.", "sucesso")
            operacao.save()
            eventos.append({"tipo": "sucesso", "mensagem": f"Bridge respondeu com sucesso em {operacao.bridge_base_url}."})
            if operacao.live_view_url or operacao.frame_snapshot_url:
                eventos.append({"tipo": "sucesso", "mensagem": "A bridge forneceu feed de vídeo/snapshot para o drone."})
        except (ValueError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            operacao.estado_conexao = "erro"
            operacao.bridge_ultimo_erro = str(exc)
            operacao.ultimo_heartbeat = timezone.now()
            _append_bridge_log(operacao, f"Falha no teste de ligação: {exc}", "erro")
            operacao.save(update_fields=["estado_conexao", "bridge_ultimo_erro", "ultimo_heartbeat", "atualizado_em"])
            eventos.append({"tipo": "erro", "mensagem": f"Falha ao contactar a bridge: {exc}"})
            return JsonResponse(
                {
                    "ok": False,
                    "eventos": eventos,
                    "estado": {
                        "estado_conexao": operacao.estado_conexao,
                        "estado_label": operacao.get_estado_conexao_display(),
                        "ultimo_heartbeat": operacao.ultimo_heartbeat.isoformat() if operacao.ultimo_heartbeat else "",
                        "feed_disponivel": bool(operacao.live_view_url or operacao.frame_snapshot_url),
                    },
                },
                status=502,
            )

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

    return JsonResponse(
        {
            "ok": True,
            "eventos": eventos,
            "estado": {
                "estado_conexao": operacao.estado_conexao,
                "estado_label": operacao.get_estado_conexao_display(),
                "ultimo_heartbeat": operacao.ultimo_heartbeat.isoformat() if operacao.ultimo_heartbeat else "",
                "feed_disponivel": bool(operacao.live_view_url or operacao.frame_snapshot_url),
            },
        }
    )


@login_required
@admin_required
@require_POST
def api_procurar_drone(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return JsonResponse({"ok": False, "eventos": [{"tipo": "erro", "mensagem": "Sem permissões para procurar o drone."}]}, status=403)
    if empresa is None:
        return JsonResponse({"ok": False, "eventos": [{"tipo": "erro", "mensagem": "A vista global não permite procurar um drone específico."}]}, status=400)

    operacao = get_object_or_404(DroneOperacaoTempoReal, empresa=empresa)
    operacao.estado_conexao = "procurando"
    operacao.ultimo_heartbeat = timezone.now()
    _append_bridge_log(operacao, "Bridge colocada em modo de procura do drone.", "info")
    operacao.save(update_fields=["estado_conexao", "ultimo_heartbeat", "atualizado_em"])

    eventos = [
        {"tipo": "info", "mensagem": f"A procurar o {operacao.equipamento} na infraestrutura local..."},
        {"tipo": "info", "mensagem": "A aguardar feed, bridge ou heartbeat do drone."},
    ]
    if operacao.live_view_url or operacao.frame_snapshot_url:
        eventos.append({"tipo": "sucesso", "mensagem": "Já existe feed configurado. O drone pode ser validado a qualquer momento."})

    return JsonResponse(
        {
            "ok": True,
            "eventos": eventos,
            "estado": {
                "estado_conexao": operacao.estado_conexao,
                "estado_label": operacao.get_estado_conexao_display(),
                "ultimo_heartbeat": operacao.ultimo_heartbeat.isoformat() if operacao.ultimo_heartbeat else "",
                "feed_disponivel": bool(operacao.live_view_url or operacao.frame_snapshot_url),
            },
        }
    )


@login_required
@admin_required
@require_GET
def api_estado_drone(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return JsonResponse({"ok": False, "eventos": [{"tipo": "erro", "mensagem": "Sem permissões para consultar o estado do drone."}]}, status=403)
    if empresa is None:
        return JsonResponse({"ok": False, "eventos": [{"tipo": "erro", "mensagem": "A vista global não tem estado de drone em tempo real."}]}, status=400)

    operacao = get_object_or_404(DroneOperacaoTempoReal, empresa=empresa)
    return JsonResponse(
        {
            "ok": True,
            "estado": {
                "estado_conexao": operacao.estado_conexao,
                "estado_label": operacao.get_estado_conexao_display(),
                "ultimo_heartbeat": operacao.ultimo_heartbeat.isoformat() if operacao.ultimo_heartbeat else "",
                "feed_disponivel": bool(operacao.live_view_url or operacao.frame_snapshot_url),
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
                "bridge_logs": _bridge_logs_context(operacao),
                "bridge_status_summary": _bridge_status_summary(operacao),
            },
        }
    )


@csrf_exempt
@require_POST
def api_bridge_ingest_estado(request):
    bridge_key = request.headers.get("X-Bridge-Key") or request.POST.get("bridge_key")
    if not bridge_key:
        return JsonResponse({"ok": False, "erro": "Bridge key em falta."}, status=403)

    operacao = _obter_operacao_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge não autorizada."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        return JsonResponse({"ok": False, "erro": f"JSON inválido: {exc.msg}"}, status=400)

    _normalizar_estado_bridge(operacao, payload)
    _append_bridge_log(operacao, "Heartbeat recebido da bridge.", "sucesso")
    _set_bridge_meta(operacao, "ultimo_heartbeat_recebido", timezone.now().isoformat())
    operacao.save()
    return JsonResponse(
        {
            "ok": True,
            "estado": {
                "estado_conexao": operacao.estado_conexao,
                "estado_label": operacao.get_estado_conexao_display(),
                "ultimo_heartbeat": operacao.ultimo_heartbeat.isoformat() if operacao.ultimo_heartbeat else "",
            },
        }
    )


@csrf_exempt
@require_GET
def api_bridge_comandos_pendentes(request):
    bridge_key = request.headers.get("X-Bridge-Key") or request.GET.get("bridge_key")
    operacao = _obter_operacao_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge não autorizada."}, status=403)

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
        DroneComandoOperacao.objects.filter(id__in=ids_pendentes).update(status="enviado")
    if comandos:
        _append_bridge_log(operacao, f"Bridge recolheu {len(comandos)} comando(s) pendente(s).", "info")
        operacao.save(update_fields=["metadados", "atualizado_em"])

    return JsonResponse({"ok": True, "comandos": comandos})


@csrf_exempt
@require_POST
def api_bridge_confirmar_comando(request, comando_id):
    bridge_key = request.headers.get("X-Bridge-Key") or request.GET.get("bridge_key")
    operacao = _obter_operacao_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge não autorizada."}, status=403)

    comando = get_object_or_404(DroneComandoOperacao, operacao=operacao, pk=comando_id)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        return JsonResponse({"ok": False, "erro": f"JSON inválido: {exc.msg}"}, status=400)

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
    _append_bridge_log(operacao, f"Comando {comando.get_tipo_comando_display()} confirmado pela bridge com estado {comando.get_status_display()}.", "sucesso" if novo_status == "executado" else "erro")
    _set_bridge_meta(
        operacao,
        "ultimo_comando_executado",
        {
            "tipo": comando.get_tipo_comando_display(),
            "status": comando.get_status_display(),
            "timestamp": timezone.now().isoformat(),
        },
    )
    _set_bridge_meta(operacao, "hora_ultima_confirmacao", timezone.now().isoformat())
    operacao.save(update_fields=["metadados", "atualizado_em"])

    return JsonResponse({"ok": True, "comando_id": str(comando.id), "status": comando.status})


@csrf_exempt
@require_POST
def api_bridge_log_event(request):
    bridge_key = request.headers.get("X-Bridge-Key") or request.POST.get("bridge_key")
    operacao = _obter_operacao_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge não autorizada."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        return JsonResponse({"ok": False, "erro": f"JSON inválido: {exc.msg}"}, status=400)

    mensagem = payload.get("mensagem") or payload.get("message") or ""
    tipo = payload.get("tipo") or payload.get("level") or "info"
    _append_bridge_log(operacao, mensagem, tipo)
    operacao.save(update_fields=["metadados", "atualizado_em"])
    return JsonResponse({"ok": True})


@login_required
@admin_required
def missao_drone_create(request, furo_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furos_qs = filtrar_queryset_por_empresa(Furo.objects.select_related("projeto"), empresa=empresa)
    furo = get_object_or_404(furos_qs, pk=furo_id)

    if request.method == "POST":
        form = MissaoDroneFuroForm(request.POST, request.FILES, furo=furo, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, "Missao do drone registada com sucesso.")
            return redirect("geologia:furo_dashboard", furo_id=furo.pk)
        messages.error(request, "Nao foi possivel guardar a missao do drone.")
    else:
        form = MissaoDroneFuroForm(furo=furo, empresa=empresa, initial={"titulo": f"Levantamento DJI Mini 4 Pro - {furo.nome}"})

    return render(
        request,
        "geologia/missao_form.html",
        {
            "form": form,
            "furo": furo,
            "titulo": f"Nova Missao de Drone - {furo.nome}",
        },
    )


@login_required
@admin_required
def missao_drone_detail(request, pk):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    missoes_qs = filtrar_queryset_por_empresa(
        MissaoDroneFuro.objects.select_related("furo", "furo__projeto"),
        empresa=empresa,
    )
    missao = get_object_or_404(missoes_qs, pk=pk)
    logs_relacionados = missao.logs_geologicos.select_related("furo").order_by("intervalo_de", "intervalo_ate")

    return render(
        request,
        "geologia/missao_detail.html",
        {
            "missao": missao,
            "furo": missao.furo,
            "logs_relacionados": logs_relacionados,
        },
    )


@login_required
@admin_required
def missao_drone_update(request, pk):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    missao = get_object_or_404(filtrar_queryset_por_empresa(MissaoDroneFuro.objects.all(), empresa=empresa), pk=pk)

    if request.method == "POST":
        form = MissaoDroneFuroForm(
            request.POST,
            request.FILES,
            instance=missao,
            furo=missao.furo,
            empresa=empresa,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Missao do drone atualizada com sucesso.")
            return redirect("geologia:missao_detail", pk=missao.pk)
        messages.error(request, "Nao foi possivel atualizar a missao do drone.")
    else:
        form = MissaoDroneFuroForm(instance=missao, furo=missao.furo, empresa=empresa)

    return render(
        request,
        "geologia/missao_form.html",
        {
            "form": form,
            "furo": missao.furo,
            "titulo": f"Editar Missao de Drone - {missao.furo.nome}",
            "missao": missao,
        },
    )
