from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from core.permissions import (
    admin_required,
    encarregado_obra_required,
    geologia_operacional_required,
    geologo_required,
)
from geologia.forms import (
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
    construir_form_comando_sf,
    criar_ou_obter_drone_sf_demo,
    motor_missoes_summary_sf,
    processar_comandos_pendentes_bridge_sf,
    processar_ingest_estado_bridge_sf,
    processar_log_event_bridge_sf,
    processar_form_modelo_sf,
    processar_execucao_missao_programada_sf,
    processar_remocao_missao_programada_sf,
    processar_toggle_missao_programada_sf,
    serializar_estado_operacao_sf,
)
from geologia.services.hub_page import (
    construir_contexto_drone_sf_hub,
    construir_contexto_geologia_hub,
)
from geologia.services.drone_sf_page import (
    processar_acao_missao_programada_sf,
    processar_fluxo_form_modelo_sf,
    processar_post_comando_sf,
    processar_post_operacao_detail_sf,
    resolver_contexto_bridge_sf,
)
from geologia.selectors.dashboard import (
    obter_comando_sf_operacao,
    obter_comandos_recentes_operacao_sf,
    obter_drone_sf,
    obter_drone_sf_simples,
    obter_furo_geologia_dashboard,
    obter_logs_furo_geologia,
    obter_missao_programada_drone_sf,
    obter_missoes_furo_geologia,
    obter_operacao_drone_sf,
    obter_operacao_sf_por_bridge_key,
    obter_ou_criar_configuracao_drone_sf,
    obter_ou_criar_operacao_drone_sf,
    obter_furos_geologia_hub_qs,
    obter_logs_geologia_hub_qs,
    obter_missoes_geologia_hub_qs,
    obter_semoforo_e_prioridades_furos_geologo,
)
from projetos.selectors.acesso import obter_empregado_por_user

from .common import obter_empresa_admin_geologia, obter_empresa_geologia_operacional


def _json_ok(payload=None, *, status=200):
    data = {"ok": True}
    if payload:
        data.update(payload)
    return JsonResponse(data, status=status)


def _json_erro(*, erro, status=400):
    return JsonResponse({"ok": False, "erro": erro}, status=status)


def _processar_post_form_modelo(
    *,
    request,
    form,
    mensagem_sucesso,
    mensagem_erro,
    redirect_name,
    redirect_kwargs,
):
    if request.method != "POST":
        return None
    resultado = processar_form_modelo_sf(
        form=form,
        mensagem_sucesso=mensagem_sucesso,
        mensagem_erro=mensagem_erro,
    )
    if resultado["ok"]:
        messages.success(request, resultado["mensagem"])
        return redirect(redirect_name, **redirect_kwargs)
    messages.error(request, resultado["mensagem"])
    return None


def _mensagem_sucesso_redirect(*, request, mensagem, redirect_name, **redirect_kwargs):
    messages.success(request, mensagem)
    return redirect(redirect_name, **redirect_kwargs)


@login_required
@admin_required
def geologia_hub(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    return render(
        request,
        "geologia/hub.html",
        construir_contexto_geologia_hub(empresa=empresa, contexto_geologia=contexto_geologia),
    )


@login_required
@geologo_required
def geologia_geologo_dashboard(request):
    empregado = obter_empregado_por_user(request.user)
    if not empregado or not empregado.empresa_id:
        messages.error(request, "A tua conta não está ligada a uma empresa para aceder à geologia.")
        return redirect("projetos:area_empregado")

    empresa = empregado.empresa
    furos_qs = obter_furos_geologia_hub_qs(empresa=empresa)
    logs_qs = obter_logs_geologia_hub_qs(empresa=empresa)
    missoes_qs = obter_missoes_geologia_hub_qs(empresa=empresa)
    semaforo_furos, top_prioritarios, metadados_score = obter_semoforo_e_prioridades_furos_geologo(
        empresa=empresa,
        limite_top=5,
    )

    return render(
        request,
        "geologia/empregado_geologo_dashboard.html",
        {
            "empregado": empregado,
            "empresa_geologia": empresa,
            "furos": furos_qs[:12],
            "logs_recentes": logs_qs[:8],
            "missoes_recentes": missoes_qs[:6],
            "total_furos": furos_qs.count(),
            "total_logs": logs_qs.count(),
            "total_missoes": missoes_qs.count(),
            "semaforo_furos": semaforo_furos,
            "top_furos_prioritarios": top_prioritarios,
            "metadados_score": metadados_score,
        },
    )


@login_required
@encarregado_obra_required
def geologia_encarregado_dashboard(request):
    empregado = obter_empregado_por_user(request.user)
    if not empregado or not empregado.empresa_id:
        messages.error(request, "A tua conta não está ligada a uma empresa para aceder à geologia.")
        return redirect("projetos:area_empregado")

    empresa = empregado.empresa
    furos_qs = obter_furos_geologia_hub_qs(empresa=empresa)
    logs_qs = obter_logs_geologia_hub_qs(empresa=empresa)
    missoes_qs = obter_missoes_geologia_hub_qs(empresa=empresa)

    return render(
        request,
        "geologia/empregado_encarregado_dashboard.html",
        {
            "empregado": empregado,
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

    return render(
        request,
        "geologia/drone_sf_hub.html",
        construir_contexto_drone_sf_hub(empresa=empresa, contexto_geologia=contexto_geologia),
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
    fluxo = processar_fluxo_form_modelo_sf(
        method=request.method,
        form=form,
        processar_form_modelo_sf_fn=processar_form_modelo_sf,
        mensagem_sucesso="Drone S_F criado com sucesso.",
        mensagem_erro="Não foi possível criar o Drone S_F.",
    )
    if fluxo["handled"]:
        if fluxo["ok"]:
            messages.success(request, fluxo["mensagem"])
            return redirect("geologia:drone_sf_detail", pk=fluxo["objeto"].pk)
        messages.error(request, fluxo["mensagem"])

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
    resposta_post = _processar_post_form_modelo(
        request=request,
        form=config_form,
        mensagem_sucesso="Configuração do Drone S_F atualizada.",
        mensagem_erro="Não foi possível atualizar a configuração do Drone S_F.",
        redirect_name="geologia:drone_sf_detail",
        redirect_kwargs={"pk": drone.pk},
    )
    if resposta_post:
        return resposta_post

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
    resposta_post = _processar_post_form_modelo(
        request=request,
        form=form,
        mensagem_sucesso="Módulo do Drone S_F criado com sucesso.",
        mensagem_erro="Não foi possível criar o módulo do Drone S_F.",
        redirect_name="geologia:drone_sf_detail",
        redirect_kwargs={"pk": drone.pk},
    )
    if resposta_post:
        return resposta_post

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
    resposta_post = _processar_post_form_modelo(
        request=request,
        form=form,
        mensagem_sucesso="Sensor do Drone S_F criado com sucesso.",
        mensagem_erro="Não foi possível criar o sensor do Drone S_F.",
        redirect_name="geologia:drone_sf_detail",
        redirect_kwargs={"pk": drone.pk},
    )
    if resposta_post:
        return resposta_post

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
    comando_form = construir_form_comando_sf(
        operacao=operacao,
        empresa=drone.empresa,
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
    resposta_post = processar_post_operacao_detail_sf(
        request_method=request.method,
        action=request.POST.get("sf_action"),
        operacao_form=operacao_form,
        missao_programada_form=missao_programada_form,
        missao_edicao=missao_edicao,
        empresa=drone.empresa,
        utilizador=request.user,
    )
    if resposta_post["handled"]:
        if resposta_post["ok"]:
            messages.success(request, resposta_post["message"])
        else:
            messages.error(request, resposta_post["message"])
        return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)

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
    resultado_comando = processar_post_comando_sf(
        request_method=request.method,
        request_post=request.POST,
        operacao=operacao,
        empresa=drone.empresa,
        utilizador=request.user,
    )
    if resultado_comando["handled"]:
        if resultado_comando["ok"]:
            messages.success(request, resultado_comando["message"])
        else:
            messages.error(request, resultado_comando["message"])
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
    resultado = processar_acao_missao_programada_sf(
        acao="toggle",
        processar_toggle_fn=processar_toggle_missao_programada_sf,
        missao=missao,
        ativa=novo_estado,
    )
    return _mensagem_sucesso_redirect(
        request=request,
        mensagem=resultado["mensagem"],
        redirect_name="geologia:drone_sf_operacao_detail",
        drone_id=drone.pk,
    )


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

    resultado = processar_acao_missao_programada_sf(
        acao="executar",
        processar_execucao_fn=processar_execucao_missao_programada_sf,
        missao=missao,
        operacao=operacao,
        utilizador=request.user,
    )
    return _mensagem_sucesso_redirect(
        request=request,
        mensagem=resultado["mensagem"],
        redirect_name="geologia:drone_sf_operacao_detail",
        drone_id=drone.pk,
    )


@login_required
@admin_required
@require_POST
def drone_sf_missao_programada_delete(request, drone_id, missao_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    missao = obter_missao_programada_drone_sf(drone=drone, missao_id=missao_id)
    resultado = processar_acao_missao_programada_sf(
        acao="remover",
        processar_remocao_fn=processar_remocao_missao_programada_sf,
        missao=missao,
    )
    return _mensagem_sucesso_redirect(
        request=request,
        mensagem=resultado["mensagem"],
        redirect_name="geologia:drone_sf_operacao_detail",
        drone_id=drone.pk,
    )


@csrf_exempt
@require_POST
def api_drone_sf_bridge_ingest_estado(request):
    contexto = resolver_contexto_bridge_sf(
        request=request,
        obter_operacao_por_bridge_key_fn=obter_operacao_sf_por_bridge_key,
        metodo="POST",
        requer_payload_json=True,
    )
    if not contexto["ok"]:
        return contexto["erro_response"]
    operacao = contexto["operacao"]
    payload = contexto["payload"]

    processar_ingest_estado_bridge_sf(operacao, payload)
    return _json_ok(
        {
            "estado": {
                "estado": operacao.estado,
                "estado_label": operacao.get_estado_display(),
                "ultimo_heartbeat": operacao.ultimo_heartbeat.isoformat() if operacao.ultimo_heartbeat else "",
            }
        }
    )


@csrf_exempt
@require_GET
def api_drone_sf_bridge_comandos_pendentes(request):
    contexto = resolver_contexto_bridge_sf(
        request=request,
        obter_operacao_por_bridge_key_fn=obter_operacao_sf_por_bridge_key,
        metodo="GET",
    )
    if not contexto["ok"]:
        return contexto["erro_response"]
    operacao = contexto["operacao"]

    comandos = processar_comandos_pendentes_bridge_sf(operacao)
    return _json_ok({"comandos": comandos})


@csrf_exempt
@require_POST
def api_drone_sf_bridge_confirmar_comando(request, comando_id):
    contexto = resolver_contexto_bridge_sf(
        request=request,
        obter_operacao_por_bridge_key_fn=obter_operacao_sf_por_bridge_key,
        metodo="POST",
        requer_payload_json=True,
    )
    if not contexto["ok"]:
        return contexto["erro_response"]
    operacao = contexto["operacao"]
    payload = contexto["payload"]

    comando = obter_comando_sf_operacao(operacao=operacao, comando_id=comando_id)
    erro_response = confirmar_comando_bridge_sf(comando=comando, payload=payload)
    if erro_response is not None:
        return erro_response
    return _json_ok({"comando_id": str(comando.id), "status": comando.status})


@csrf_exempt
@require_POST
def api_drone_sf_bridge_log_event(request):
    contexto = resolver_contexto_bridge_sf(
        request=request,
        obter_operacao_por_bridge_key_fn=obter_operacao_sf_por_bridge_key,
        metodo="POST",
        requer_payload_json=True,
    )
    if not contexto["ok"]:
        return contexto["erro_response"]
    operacao = contexto["operacao"]
    payload = contexto["payload"]

    processar_log_event_bridge_sf(operacao, payload)
    return _json_ok()


@login_required
@admin_required
@require_GET
def api_drone_sf_estado(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return _json_erro(erro="Sem permissões para consultar o estado do Drone S_F.", status=403)

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    operacao, _ = obter_ou_criar_operacao_drone_sf(drone)
    return _json_ok({"estado": serializar_estado_operacao_sf(operacao)})


@login_required
@geologia_operacional_required
def furo_geologia_dashboard(request, furo_id):
    empresa, _, resposta_erro = obter_empresa_geologia_operacional(request)
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
