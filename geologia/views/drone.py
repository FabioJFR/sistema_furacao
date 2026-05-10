from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from core.permissions import admin_required
from geologia.forms import (
    DroneOperacaoTempoRealForm,
)
from geologia.selectors.drone import (
    obter_comando_operacao_drone,
    obter_comandos_recentes_operacao_drone,
    obter_furo_drone,
    obter_furos_hub_drone_qs,
    obter_logs_relacionados_missao,
    obter_missao_drone,
    obter_missoes_hub_drone_qs,
    obter_operacao_empresa,
    obter_operacao_por_bridge_key as obter_operacao_por_bridge_key_selector,
    obter_ou_criar_operacao_empresa,
)
from geologia.services.drone_dashboard import (
    colocar_drone_em_procura,
    confirmar_comando_bridge,
    construir_form_comando,
    construir_form_missao_create,
    construir_form_missao_update,
    parse_payload_json_request,
    processar_fluxo_comando_drone_create,
    processar_fluxo_operacao_drone_update,
    processar_fluxo_importacao_missao,
    processar_comandos_pendentes_bridge,
    processar_ingest_estado_bridge,
    processar_log_event_bridge,
    processar_fluxo_form_missao,
    processar_missao_create,
    processar_missao_update,
    serializar_estado_operacao,
    testar_ligacao_drone,
)

from .common import obter_empresa_admin_geologia


def _json_ok(payload=None, *, status=200):
    data = {"ok": True}
    if payload:
        data.update(payload)
    return JsonResponse(data, status=status)


def _json_erro(*, mensagem=None, erro=None, status=400, eventos=None):
    data = {"ok": False}
    if erro is not None:
        data["erro"] = erro
    if eventos is not None:
        data["eventos"] = eventos
    elif mensagem is not None:
        data["eventos"] = [{"tipo": "erro", "mensagem": mensagem}]
    return JsonResponse(data, status=status)


def _obter_operacao_por_bridge_key(bridge_key):
    return obter_operacao_por_bridge_key_selector(bridge_key)


def _obter_bridge_key_header(request):
    return (request.headers.get("X-Bridge-Key") or "").strip()


def _validar_bridge_key_header(request):
    bridge_key = _obter_bridge_key_header(request)
    if not bridge_key:
        return None, _json_erro(
            erro="Bridge key em falta. Use o header X-Bridge-Key.",
            status=403,
        )
    return bridge_key, None


def _validar_empresa_geologia_necessaria(empresa, mensagem_erro):
    if empresa is not None:
        return None
    return mensagem_erro


@login_required
@admin_required
def drone_hub(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furos_qs = obter_furos_hub_drone_qs(empresa=empresa)
    missoes_qs = obter_missoes_hub_drone_qs(empresa=empresa)
    furos = list(furos_qs[:12])
    missoes_recentes = list(missoes_qs[:8])
    operacao = None
    operacao_form = None
    comando_form = None
    comandos_recentes = []
    if empresa is not None:
        operacao, _ = obter_ou_criar_operacao_empresa(empresa)
        estado_operacao = serializar_estado_operacao(operacao)
        operacao_form = DroneOperacaoTempoRealForm(
            request.POST or None,
            instance=operacao,
            empresa=empresa,
            prefix="operacao",
        )
        comando_form = construir_form_comando(operacao=operacao, empresa=empresa)
        comandos_recentes = obter_comandos_recentes_operacao_drone(operacao, limit=10)
    else:
        estado_operacao = {}

    fluxo_importacao = processar_fluxo_importacao_missao(
        request_method=request.method,
        request_post=request.POST,
        request_files=request.FILES,
        empresa=empresa,
        action_value=request.POST.get("drone_action"),
    )
    form = fluxo_importacao["form"]
    resultado_importacao = fluxo_importacao["resultado"]
    if resultado_importacao:
        if resultado_importacao["ok"]:
            missao = resultado_importacao["missao"]
            messages.success(request, "Missao DJI importada com sucesso.")
            return redirect("geologia:missao_detail", pk=missao.pk)
        messages.error(request, "Nao foi possivel importar a missao DJI.")

    context = {
        "form": form,
        "contexto_geologia": contexto_geologia,
        "empresa_geologia": empresa,
        "operacao_form": operacao_form,
        "comando_form": comando_form,
        "operacao": operacao,
        "bridge_logs": estado_operacao.get("bridge_logs", []),
        "bridge_status_summary": estado_operacao.get("bridge_status_summary", {}),
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
    erro_empresa = _validar_empresa_geologia_necessaria(
        empresa,
        "O controlo em tempo real do drone precisa de uma empresa selecionada.",
    )
    if erro_empresa:
        messages.error(request, erro_empresa)
        return redirect("geologia:drone_hub")

    operacao = obter_operacao_empresa(empresa)
    fluxo = processar_fluxo_operacao_drone_update(
        request_method=request.method,
        request_post=request.POST,
        operacao=operacao,
        empresa=empresa,
    )
    resultado = fluxo["resultado"]
    if resultado is not None:
        if resultado["ok"]:
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
    erro_empresa = _validar_empresa_geologia_necessaria(
        empresa,
        "Os comandos do drone precisam de uma empresa selecionada.",
    )
    if erro_empresa:
        messages.error(request, erro_empresa)
        return redirect("geologia:drone_hub")

    operacao = obter_operacao_empresa(empresa)
    fluxo = processar_fluxo_comando_drone_create(
        request_method=request.method,
        request_post=request.POST,
        operacao=operacao,
        empresa=empresa,
        user=request.user,
    )
    resultado = fluxo["resultado"]
    if resultado is not None:
        if resultado["ok"]:
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
        return _json_erro(mensagem="Sem permissões para testar a ligação do drone.", status=403)
    if empresa is None:
        return _json_erro(mensagem="A vista global não permite testar a ligação a um drone específico.", status=400)

    operacao = obter_operacao_empresa(empresa)
    ok, eventos, estado = testar_ligacao_drone(operacao)
    if ok:
        return _json_ok({"eventos": eventos, "estado": estado})
    return _json_erro(eventos=eventos, status=502)


@login_required
@admin_required
@require_POST
def api_procurar_drone(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return _json_erro(mensagem="Sem permissões para procurar o drone.", status=403)
    if empresa is None:
        return _json_erro(mensagem="A vista global não permite procurar um drone específico.", status=400)

    operacao = obter_operacao_empresa(empresa)
    eventos = colocar_drone_em_procura(operacao)

    return _json_ok({"eventos": eventos, "estado": serializar_estado_operacao(operacao)})


@login_required
@admin_required
@require_GET
def api_estado_drone(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return _json_erro(mensagem="Sem permissões para consultar o estado do drone.", status=403)
    if empresa is None:
        return _json_erro(mensagem="A vista global não tem estado de drone em tempo real.", status=400)

    operacao = obter_operacao_empresa(empresa)
    return _json_ok({"estado": serializar_estado_operacao(operacao)})


@csrf_exempt
@require_POST
def api_bridge_ingest_estado(request):
    bridge_key, erro_response = _validar_bridge_key_header(request)
    if erro_response is not None:
        return erro_response

    operacao = _obter_operacao_por_bridge_key(bridge_key)
    if operacao is None:
        return _json_erro(erro="Bridge não autorizada.", status=403)

    payload, erro_response = parse_payload_json_request(request)
    if erro_response is not None:
        return erro_response

    processar_ingest_estado_bridge(operacao, payload)
    return _json_ok(
        {
            "estado": {
                "estado_conexao": operacao.estado_conexao,
                "estado_label": operacao.get_estado_conexao_display(),
                "ultimo_heartbeat": operacao.ultimo_heartbeat.isoformat() if operacao.ultimo_heartbeat else "",
            }
        }
    )


@csrf_exempt
@require_GET
def api_bridge_comandos_pendentes(request):
    bridge_key, erro_response = _validar_bridge_key_header(request)
    if erro_response is not None:
        return erro_response
    operacao = _obter_operacao_por_bridge_key(bridge_key)
    if operacao is None:
        return _json_erro(erro="Bridge não autorizada.", status=403)

    comandos = processar_comandos_pendentes_bridge(operacao)

    return _json_ok({"comandos": comandos})


@csrf_exempt
@require_POST
def api_bridge_confirmar_comando(request, comando_id):
    bridge_key, erro_response = _validar_bridge_key_header(request)
    if erro_response is not None:
        return erro_response
    operacao = _obter_operacao_por_bridge_key(bridge_key)
    if operacao is None:
        return _json_erro(erro="Bridge não autorizada.", status=403)

    comando = obter_comando_operacao_drone(operacao=operacao, comando_id=comando_id)
    payload, erro_response = parse_payload_json_request(request)
    if erro_response is not None:
        return erro_response

    erro_response = confirmar_comando_bridge(comando=comando, payload=payload)
    if erro_response is not None:
        return erro_response

    return _json_ok({"comando_id": str(comando.id), "status": comando.status})


@csrf_exempt
@require_POST
def api_bridge_log_event(request):
    bridge_key, erro_response = _validar_bridge_key_header(request)
    if erro_response is not None:
        return erro_response
    operacao = _obter_operacao_por_bridge_key(bridge_key)
    if operacao is None:
        return _json_erro(erro="Bridge não autorizada.", status=403)

    payload, erro_response = parse_payload_json_request(request)
    if erro_response is not None:
        return erro_response

    processar_log_event_bridge(operacao, payload)
    return _json_ok()


@login_required
@admin_required
def missao_drone_create(request, furo_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furo = obter_furo_drone(furo_id, empresa=empresa)

    fluxo = processar_fluxo_form_missao(
        request_method=request.method,
        request_post=request.POST,
        request_files=request.FILES,
        processar_fn=processar_missao_create,
        construir_form_fn=construir_form_missao_create,
        construir_form_kwargs={"furo": furo, "empresa": empresa},
        processar_kwargs={"furo": furo, "empresa": empresa},
    )
    form = fluxo["form"]
    if fluxo["ok"] is True:
        messages.success(request, "Missao do drone registada com sucesso.")
        return redirect("geologia:furo_dashboard", furo_id=furo.pk)
    if fluxo["ok"] is False:
        messages.error(request, "Nao foi possivel guardar a missao do drone.")

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

    missao = obter_missao_drone(pk, empresa=empresa)
    logs_relacionados = obter_logs_relacionados_missao(missao)

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

    missao = obter_missao_drone(pk, empresa=empresa)

    fluxo = processar_fluxo_form_missao(
        request_method=request.method,
        request_post=request.POST,
        request_files=request.FILES,
        processar_fn=processar_missao_update,
        construir_form_fn=construir_form_missao_update,
        construir_form_kwargs={"missao": missao, "empresa": empresa},
        processar_kwargs={"missao": missao, "empresa": empresa},
    )
    form = fluxo["form"]
    if fluxo["ok"] is True:
        messages.success(request, "Missao do drone atualizada com sucesso.")
        return redirect("geologia:missao_detail", pk=missao.pk)
    if fluxo["ok"] is False:
        messages.error(request, "Nao foi possivel atualizar a missao do drone.")

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
