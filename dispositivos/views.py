# dispositivos/views.py
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_GET, require_POST
from dispositivos.services.serial_service import (
    listar_portas_seriais,
)
from dispositivos.selectors.dashboard import (
    obter_dispositivo_ativo,
    construir_contexto_captura_dispositivo,
    obter_empregado_por_user_empresa,
    obter_furo,
    anexar_sessao_ao_preview,
    obter_leitura_detail,
    obter_sessao_detail,
    resolver_empresa_para_registo_por_furo,
)
from dispositivos.services.dashboard import (
    processar_escuta_dispositivo_detectado,
    processar_inspecao_bluetooth_detectado,
    processar_procura_dispositivos_bluetooth,
    processar_registo_dispositivo_detectado,
    processar_teste_leitura_usb,
)
from dispositivos.services.importacao_historico import (
    render_historico_importacao_csv,
)
from dispositivos.services.dashboard_import import processar_preview_importacao_magcruiser_texto
from dispositivos.selectors.importacao_historico import obter_historico_importacao
from dispositivos.services.captura_page import (
    listar_historico_importacoes_seguro,
    processar_captura_leitura_serial_sessao,
    processar_post_captura_dispositivo,
)
from dispositivos.services.api_flow import (
    construir_http_response_operacao_api,
    construir_payload_dispositivo_guardado,
    construir_payload_escuta_dispositivo,
)
from dispositivos.services.dashboard_page import (
    construir_contexto_dashboard_dispositivos,
    construir_contexto_leituras_brutas_dispositivo,
    construir_contexto_lista_dispositivos,
    construir_contexto_sessao_dispositivo_detail,
    construir_contexto_sessoes_dispositivo,
    construir_contexto_shots_dispositivo,
)
from django.http import JsonResponse, HttpResponse
import random
import time

MAGCRUISER_PREVIEW_SESSION_KEY = "magcruiser_import_preview"
MAGCRUISER_REPORT_SESSION_KEY = "magcruiser_import_report"


def _obter_empresa_id_utilizador(request):
    if request.user.is_superuser:
        return None
    raise PermissionDenied("A área de dispositivos está disponível apenas para administradores.")


def _garantir_admin_api(request):
    if not request.user.is_authenticated:
        raise PermissionDenied("Autenticação obrigatória.")
    if not request.user.is_superuser:
        raise PermissionDenied("A área de dispositivos está disponível apenas para administradores.")


def _json_ok(payload=None, *, status=200):
    data = {"ok": True}
    if payload:
        data.update(payload)
    return JsonResponse(data, status=status)


def _json_erro(mensagem, *, status=400, eventos=None):
    data = {
        "ok": False,
        "eventos": eventos or [{"tipo": "erro", "mensagem": mensagem}],
    }
    return JsonResponse(data, status=status)


def _resolver_empresa_para_registo(request):
    furo_id = (request.POST.get("furo_id") or "").strip()
    return resolver_empresa_para_registo_por_furo(furo_id)


@login_required
def api_testar(request):
    return JsonResponse({
        "status": "ok",
        "msg": "Ligação simulada com sucesso"
    })


@login_required
def api_capturar(request):
    # Simulação de leitura real
    fake_payload = {
        "depth": random.randint(10, 100),
        "inclination": round(random.uniform(-10, 10), 2),
        "azimuth": round(random.uniform(0, 360), 2),
        "timestamp": time.time()
    }

    return JsonResponse({
        "status": "ok",
        "payload": fake_payload
    })


@login_required
@require_GET
def api_procurar_portas_usb(request):
    _garantir_admin_api(request)

    portas = listar_portas_seriais()
    eventos = [
        {"tipo": "info", "mensagem": "A procurar portas USB/serial disponíveis..."},
        {"tipo": "info", "mensagem": f"Foram encontradas {len(portas)} portas."},
    ]

    return _json_ok({"eventos": eventos, "portas": portas})


@login_required
@require_GET
def api_procurar_dispositivos_bluetooth(request):
    _garantir_admin_api(request)
    resultado = processar_procura_dispositivos_bluetooth()
    return construir_http_response_operacao_api(
        resultado=resultado,
        payload_sucesso=lambda r: {
            "eventos": r["eventos"],
            "dispositivos": r["dispositivos"],
        },
        mensagem_erro_padrao="Falha na procura Bluetooth.",
        json_ok_fn=_json_ok,
        json_erro_fn=_json_erro,
    )


@login_required
@require_POST
def api_testar_leitura_usb(request):
    _garantir_admin_api(request)
    resultado = processar_teste_leitura_usb(dispositivo_id=request.POST.get("dispositivo_id"))
    return construir_http_response_operacao_api(
        resultado=resultado,
        payload_sucesso=lambda r: {
            "eventos": r["eventos"],
            "leitura": r["leitura"],
        },
        mensagem_erro_padrao="Falha no teste de leitura USB.",
        json_ok_fn=_json_ok,
        json_erro_fn=_json_erro,
    )


@login_required
@require_POST
def api_inspecionar_dispositivo_bluetooth(request):
    _garantir_admin_api(request)

    address = (request.POST.get("address") or "").strip()
    name = (request.POST.get("name") or "").strip()
    resultado = processar_inspecao_bluetooth_detectado(address=address, name=name)
    return construir_http_response_operacao_api(
        resultado=resultado,
        payload_sucesso=lambda r: {
            "eventos": r["eventos"],
            "inspecao": r["inspecao"],
        },
        mensagem_erro_padrao="Falha na inspeção Bluetooth.",
        json_ok_fn=_json_ok,
        json_erro_fn=_json_erro,
    )


@login_required
@require_POST
def api_guardar_dispositivo_detectado(request):
    _garantir_admin_api(request)

    canal = (request.POST.get("canal") or "").strip()
    nome = (request.POST.get("name") or "").strip() or "Dispositivo detetado"
    identificador = (request.POST.get("identifier") or "").strip()
    descricao = (request.POST.get("description") or "").strip()
    baudrate = int((request.POST.get("baudrate") or "115200").strip() or 115200)

    try:
        empresa = _resolver_empresa_para_registo(request)
        resultado = processar_registo_dispositivo_detectado(
            empresa=empresa,
            canal=canal,
            nome=nome,
            identificador=identificador,
            descricao=descricao,
            baudrate=baudrate,
        )
        return construir_http_response_operacao_api(
            resultado=resultado,
            payload_sucesso=construir_payload_dispositivo_guardado,
            mensagem_erro_padrao=resultado.get("erro", "Falha ao guardar dispositivo."),
            json_ok_fn=_json_ok,
            json_erro_fn=_json_erro,
        )
    except Exception as exc:
        return _json_erro(f"Não foi possível guardar o dispositivo: {exc}", status=400)


@login_required
@require_POST
def api_escutar_dispositivo_detectado(request):
    _garantir_admin_api(request)

    canal = (request.POST.get("canal") or "").strip()
    identificador = (request.POST.get("identifier") or "").strip()
    nome = (request.POST.get("name") or "").strip() or identificador or "Dispositivo"
    baudrate = int((request.POST.get("baudrate") or "115200").strip() or 115200)

    resultado = processar_escuta_dispositivo_detectado(
        canal=canal,
        identificador=identificador,
        nome=nome,
        baudrate=baudrate,
    )
    return construir_http_response_operacao_api(
        resultado=resultado,
        payload_sucesso=construir_payload_escuta_dispositivo,
        mensagem_erro_padrao="Falha na escuta do dispositivo.",
        json_ok_fn=_json_ok,
        json_erro_fn=_json_erro,
    )

@login_required
def dispositivos_dashboard(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    context = construir_contexto_dashboard_dispositivos(empresa_id=empresa_id)
    return render(request, "dispositivos/dashboard.html", context)


@login_required
def sessao_dispositivo_list(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    return render(
        request,
        "dispositivos/sessao_list.html",
        construir_contexto_sessoes_dispositivo(empresa_id=empresa_id),
    )


@login_required
def leitura_bruta_list(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    return render(
        request,
        "dispositivos/leitura_bruta_list.html",
        construir_contexto_leituras_brutas_dispositivo(empresa_id=empresa_id),
    )


@login_required
def survey_shot_list(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    return render(
        request,
        "dispositivos/survey_shot_list.html",
        construir_contexto_shots_dispositivo(empresa_id=empresa_id),
    )


@login_required
def dispositivo_list(request):
    """
    Lista todos os dispositivos registados no sistema.
    Futuramente pode ser filtrado por empresa, projeto, estado, tipo, etc.
    """
    empresa_id = _obter_empresa_id_utilizador(request)
    return render(
        request,
        "dispositivos/dispositivo_list.html",
        construir_contexto_lista_dispositivos(empresa_id=empresa_id),
    )


@login_required
def sessao_dispositivo_detail(request, pk):
    empresa_id = _obter_empresa_id_utilizador(request)
    return render(
        request,
        "dispositivos/sessao_detail.html",
        construir_contexto_sessao_dispositivo_detail(pk=pk, empresa_id=empresa_id),
    )


@login_required
def leitura_bruta_detail(request, pk):
    empresa_id = _obter_empresa_id_utilizador(request)
    leitura = obter_leitura_detail(pk=pk, empresa_id=empresa_id)

    context = {
        "leitura": leitura,
    }
    return render(request, "dispositivos/leitura_bruta_detail.html", context)


@login_required
@require_POST
def capturar_leitura_serial_view(request, pk):
    empresa_id = _obter_empresa_id_utilizador(request)
    sessao = obter_sessao_detail(pk=pk, empresa_id=empresa_id)

    resultado = processar_captura_leitura_serial_sessao(sessao=sessao)
    if resultado["message_level"] == "success":
        messages.success(request, resultado["message"])
    else:
        messages.error(request, resultado["message"])

    return redirect("dispositivos:sessao_detail", pk=sessao.pk)

@login_required
def captura_dispositivo(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    empregado = obter_empregado_por_user_empresa(request.user, empresa_id=empresa_id)

    preview_data = request.session.get(MAGCRUISER_PREVIEW_SESSION_KEY)
    report_data = request.session.get(MAGCRUISER_REPORT_SESSION_KEY)
    preview_data = anexar_sessao_ao_preview(preview_data, empresa_id=empresa_id)
    historico_resultado = listar_historico_importacoes_seguro(empresa_id=empresa_id)
    historico_importacoes = historico_resultado["historico"]
    if historico_resultado["mensagem_warning"]:
        messages.warning(request, historico_resultado["mensagem_warning"])

    if request.method == "POST":
        action = (request.POST.get("action") or "create_session").strip()
        post_resultado = processar_post_captura_dispositivo(
            action=action,
            empresa_id=empresa_id,
            empregado=empregado,
            request_post=request.POST,
            request_files=request.FILES,
            request_session=request.session,
            utilizador=request.user,
            preview_session_key=MAGCRUISER_PREVIEW_SESSION_KEY,
            report_session_key=MAGCRUISER_REPORT_SESSION_KEY,
        )
        if post_resultado["message_level"] == "success":
            messages.success(request, post_resultado["message"])
        elif post_resultado["message_level"] == "info":
            messages.info(request, post_resultado["message"])
        elif post_resultado["message_level"] == "error":
            messages.error(request, post_resultado["message"])
        return redirect(
            post_resultado["redirect_name"],
            **post_resultado["redirect_kwargs"],
        )

    contexto_base = construir_contexto_captura_dispositivo(empresa_id=empresa_id)
    return render(request, "dispositivos/captura.html", {
        **contexto_base,
        "magcruiser_preview": preview_data,
        "magcruiser_report": report_data,
        "historico_importacoes": historico_importacoes,
    })


@login_required
@require_POST
def api_web_bluetooth_preview_import(request):
    _garantir_admin_api(request)

    sessao_id = (request.POST.get("sessao_importacao_id") or "").strip()
    payload_texto = request.POST.get("payload_texto") or ""
    nome_ficheiro = (request.POST.get("nome_ficheiro") or "webbluetooth_import.csv").strip()
    if not sessao_id:
        return _json_erro("Seleciona uma sessão de destino para a importação.", status=400)

    try:
        preview_data = processar_preview_importacao_magcruiser_texto(
            empresa_id=_obter_empresa_id_utilizador(request),
            sessao_id=sessao_id,
            payload_texto=payload_texto,
            nome_ficheiro=nome_ficheiro,
        )
        request.session[MAGCRUISER_PREVIEW_SESSION_KEY] = preview_data
        request.session.modified = True
    except Exception as exc:
        return _json_erro(f"Falha ao preparar pré-visualização Web Bluetooth: {exc}", status=400)

    return _json_ok(
        {
            "eventos": [
                {
                    "tipo": "sucesso",
                    "mensagem": (
                        f"Pré-visualização Web Bluetooth carregada: {preview_data['total_linhas']} "
                        f"linhas em {preview_data['filename']}."
                    ),
                }
            ],
            "preview": {
                "filename": preview_data["filename"],
                "total_linhas": preview_data["total_linhas"],
                "formato": preview_data["formato"],
            },
        }
    )


@login_required
@require_GET
def importacao_historico_csv(request, pk):
    empresa_id = _obter_empresa_id_utilizador(request)
    historico = obter_historico_importacao(pk=pk, empresa_id=empresa_id)
    csv_content = render_historico_importacao_csv(historico)
    response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="importacao-magcruiser-{historico.pk}.csv"'
    return response
