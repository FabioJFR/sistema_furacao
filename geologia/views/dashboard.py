from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
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
from geologia.services.drone_sf_dashboard import (
    bridge_logs_context_sf,
    bridge_status_summary_sf,
    construir_missoes_programadas_contexto,
    confirmar_comando_bridge_sf,
    criar_comando_drone_sf_from_form,
    criar_ou_obter_drone_sf_demo,
    executar_missao_programada_sf,
    motor_missoes_summary_sf,
    parse_payload_json_request_sf,
    processar_acao_operacao_detail_sf,
    processar_comandos_pendentes_bridge_sf,
    processar_ingest_estado_bridge_sf,
    processar_log_event_bridge_sf,
    serializar_estado_operacao_sf,
)
from geologia.selectors_dashboard import (
    listar_documentos_knowledge_base_drone,
    obter_comando_sf_operacao,
    obter_comandos_recentes_operacao_sf,
    obter_drone_sf,
    obter_drone_sf_simples,
    obter_drones_sf_hub_qs,
    obter_furo_geologia_dashboard,
    obter_furos_geologia_hub_qs,
    obter_logs_furo_geologia,
    obter_logs_geologia_hub_qs,
    obter_missao_programada_drone_sf,
    obter_missoes_furo_geologia,
    obter_missoes_geologia_hub_qs,
    obter_operacao_drone_sf,
    obter_operacao_sf_por_bridge_key,
    obter_ou_criar_configuracao_drone_sf,
    obter_ou_criar_operacao_drone_sf,
)

from .common import obter_empresa_admin_geologia


@login_required
@admin_required
def geologia_hub(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furos_qs = obter_furos_geologia_hub_qs(empresa=empresa)
    logs_qs = obter_logs_geologia_hub_qs(empresa=empresa)
    missoes_qs = obter_missoes_geologia_hub_qs(empresa=empresa)

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

    furos_qs = obter_furos_geologia_hub_qs(empresa=empresa)
    drones_qs = obter_drones_sf_hub_qs(empresa=empresa)
    missoes_qs = obter_missoes_geologia_hub_qs(empresa=empresa)
    documentos_drone = listar_documentos_knowledge_base_drone()

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

    drone = criar_ou_obter_drone_sf_demo(empresa=empresa)
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

    drone = obter_drone_sf(pk=pk, empresa=empresa)
    configuracao, _ = obter_ou_criar_configuracao_drone_sf(drone)
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

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
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

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
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

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    missao_edicao = None
    missao_edicao_id = request.GET.get("editar_missao") or request.POST.get("missao_programada_id")
    if missao_edicao_id:
        missao_edicao = obter_missao_programada_drone_sf(drone=drone, missao_id=missao_edicao_id)
    operacao, _ = obter_ou_criar_operacao_drone_sf(drone)
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
    if request.method == "POST":
        resultado_acao = processar_acao_operacao_detail_sf(
            action=request.POST.get("sf_action"),
            operacao_form=operacao_form,
            missao_programada_form=missao_programada_form,
            missao_edicao=missao_edicao,
            empresa=drone.empresa,
            utilizador=request.user,
        )
        if resultado_acao.get("handled"):
            if resultado_acao.get("ok"):
                messages.success(request, resultado_acao.get("message"))
                return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)
            messages.error(request, resultado_acao.get("message"))

    missoes_programadas = construir_missoes_programadas_contexto(drone, limit=20)

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
            "comandos_recentes": obter_comandos_recentes_operacao_sf(operacao, limit=10),
            "missoes_programadas": missoes_programadas,
            "bridge_logs": bridge_logs_context_sf(operacao),
            "bridge_status_summary": bridge_status_summary_sf(operacao),
            "motor_missoes_summary": motor_missoes_summary_sf(operacao),
            "empresa_geologia": empresa,
        },
    )


@login_required
@admin_required
def drone_sf_comando_create(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    operacao = obter_operacao_drone_sf(drone)
    form = ComandoDroneSFOperacaoForm(request.POST or None, prefix="comando_sf", operacao=operacao, empresa=drone.empresa)
    if request.method == "POST":
        if form.is_valid():
            criar_comando_drone_sf_from_form(form=form, operacao=operacao, utilizador=request.user)
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

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    missao = obter_missao_programada_drone_sf(drone=drone, missao_id=missao_id)

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

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    operacao = obter_operacao_drone_sf(drone)
    missao = obter_missao_programada_drone_sf(drone=drone, missao_id=missao_id)

    executar_missao_programada_sf(operacao=operacao, missao=missao, utilizador=request.user)
    messages.success(request, "Missão programada enviada para execução imediata na fila do Drone S_F.")
    return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)


@login_required
@admin_required
@require_POST
def drone_sf_missao_programada_delete(request, drone_id, missao_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    missao = obter_missao_programada_drone_sf(drone=drone, missao_id=missao_id)
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

    operacao = obter_operacao_sf_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge S_F não autorizada."}, status=403)

    payload, erro_response = parse_payload_json_request_sf(request)
    if erro_response is not None:
        return erro_response

    processar_ingest_estado_bridge_sf(operacao, payload)
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
    operacao = obter_operacao_sf_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge S_F não autorizada."}, status=403)

    comandos = processar_comandos_pendentes_bridge_sf(operacao)
    return JsonResponse({"ok": True, "comandos": comandos})


@csrf_exempt
@require_POST
def api_drone_sf_bridge_confirmar_comando(request, comando_id):
    bridge_key = request.headers.get("X-Bridge-Key") or request.GET.get("bridge_key")
    operacao = obter_operacao_sf_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge S_F não autorizada."}, status=403)

    comando = obter_comando_sf_operacao(operacao=operacao, comando_id=comando_id)
    payload, erro_response = parse_payload_json_request_sf(request)
    if erro_response is not None:
        return erro_response

    erro_response = confirmar_comando_bridge_sf(comando=comando, payload=payload)
    if erro_response is not None:
        return erro_response
    return JsonResponse({"ok": True, "comando_id": str(comando.id), "status": comando.status})


@csrf_exempt
@require_POST
def api_drone_sf_bridge_log_event(request):
    bridge_key = request.headers.get("X-Bridge-Key") or request.POST.get("bridge_key")
    operacao = obter_operacao_sf_por_bridge_key(bridge_key)
    if operacao is None:
        return JsonResponse({"ok": False, "erro": "Bridge S_F não autorizada."}, status=403)

    payload, erro_response = parse_payload_json_request_sf(request)
    if erro_response is not None:
        return erro_response

    processar_log_event_bridge_sf(operacao, payload)
    return JsonResponse({"ok": True})


@login_required
@admin_required
@require_GET
def api_drone_sf_estado(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return JsonResponse({"ok": False, "erro": "Sem permissões para consultar o estado do Drone S_F."}, status=403)

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    operacao, _ = obter_ou_criar_operacao_drone_sf(drone)
    return JsonResponse(
        {
            "ok": True,
            "estado": serializar_estado_operacao_sf(operacao),
        }
    )


@login_required
@admin_required
def furo_geologia_dashboard(request, furo_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furo = obter_furo_geologia_dashboard(furo_id=furo_id, empresa=empresa)
    logs = obter_logs_furo_geologia(furo)
    missoes = obter_missoes_furo_geologia(furo)

    return render(
        request,
        "geologia/furo_dashboard.html",
        {
            "furo": furo,
            "logs": logs,
            "missoes": missoes,
        },
    )
