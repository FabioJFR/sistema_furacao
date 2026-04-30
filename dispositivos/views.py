# dispositivos/views.py
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_GET, require_POST
from dispositivos.services.serial_service import (
    capturar_leitura_serial_para_sessao,
    listar_portas_seriais,
)
from dispositivos.selectors.dashboard import (
    obter_dispositivos_qs,
    obter_dispositivo_ativo,
    construir_contexto_captura_dispositivo,
    obter_empregado_por_user_empresa,
    obter_furo,
    anexar_sessao_ao_preview,
    obter_leitura_detail,
    obter_leituras_qs,
    obter_sessao_detail,
    obter_sessoes_qs,
    obter_shots_qs,
    resolver_empresa_para_registo_por_furo,
)
from dispositivos.services.dashboard import (
    processar_criacao_sessao_captura,
    processar_escuta_dispositivo_detectado,
    processar_inspecao_bluetooth_detectado,
    processar_procura_dispositivos_bluetooth,
    processar_registo_dispositivo_detectado,
    processar_teste_leitura_usb,
)
from dispositivos.services.importacao_historico import (
    render_historico_importacao_csv,
)
from dispositivos.services.dashboard_import import (
    processar_acao_importacao_magcruiser,
)
from dispositivos.selectors.importacao_historico import (
    listar_historico_importacoes_qs,
    obter_historico_importacao,
)
from django.http import JsonResponse, HttpResponse
from django.db import ProgrammingError
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
    if resultado["ok"]:
        return _json_ok(
            {"eventos": resultado["eventos"], "dispositivos": resultado["dispositivos"]}
        )
    return _json_erro(
        "Falha na procura Bluetooth.",
        status=resultado.get("status", 400),
        eventos=resultado["eventos"],
    )


@login_required
@require_POST
def api_testar_leitura_usb(request):
    _garantir_admin_api(request)
    resultado = processar_teste_leitura_usb(dispositivo_id=request.POST.get("dispositivo_id"))
    if resultado["ok"]:
        return _json_ok({"eventos": resultado["eventos"], "leitura": resultado["leitura"]})
    return _json_erro(
        "Falha no teste de leitura USB.",
        status=resultado.get("status", 400),
        eventos=resultado["eventos"],
    )


@login_required
@require_POST
def api_inspecionar_dispositivo_bluetooth(request):
    _garantir_admin_api(request)

    address = (request.POST.get("address") or "").strip()
    name = (request.POST.get("name") or "").strip()
    resultado = processar_inspecao_bluetooth_detectado(address=address, name=name)
    if resultado["ok"]:
        return _json_ok({"eventos": resultado["eventos"], "inspecao": resultado["inspecao"]})
    return _json_erro(
        "Falha na inspeção Bluetooth.",
        status=resultado.get("status", 400),
        eventos=resultado["eventos"],
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
        if not resultado["ok"]:
            return _json_erro(
                resultado["erro"],
                status=resultado.get("status", 400),
            )
        dispositivo = resultado["dispositivo"]
        eventos = resultado["eventos"]

        return _json_ok(
            {
                "eventos": eventos,
                "dispositivo": {
                    "id": str(dispositivo.pk),
                    "nome": dispositivo.nome,
                    "canal": dispositivo.canal,
                    "identificador": dispositivo.porta or dispositivo.mac_address or dispositivo.identificador_fisico,
                },
            }
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
    if resultado["ok"]:
        response = {
            "eventos": resultado["eventos"],
            "modo": resultado["modo"],
        }
        if resultado.get("leitura") is not None:
            response["leitura"] = resultado["leitura"]
        if resultado.get("inspecao") is not None:
            response["inspecao"] = resultado["inspecao"]
        return _json_ok(response)
    return _json_erro(
        "Falha na escuta do dispositivo.",
        status=resultado.get("status", 400),
        eventos=resultado["eventos"],
    )

@login_required
def dispositivos_dashboard(request):
    empresa_id = _obter_empresa_id_utilizador(request)

    dispositivos_qs = obter_dispositivos_qs(empresa_id)
    sessoes_qs = obter_sessoes_qs(empresa_id)
    leituras_qs = obter_leituras_qs(empresa_id)
    shots_qs = obter_shots_qs(empresa_id)

    total_dispositivos = dispositivos_qs.count()
    total_ativos = dispositivos_qs.filter(ativo=True).count()
    total_sessoes = sessoes_qs.count()
    total_leituras_brutas = leituras_qs.count()
    total_shots = shots_qs.count()

    ultima_sessao = (
        sessoes_qs.select_related("dispositivo", "empregado", "furo", "empresa")
        .order_by("-iniciado_em")
        .first()
    )

    ultima_leitura_bruta = (
        leituras_qs.select_related("sessao", "empresa")
        .order_by("-recebido_em")
        .first()
    )

    ultimo_shot = (
        shots_qs.select_related("sessao", "furo", "empresa")
        .order_by("-criado_em")
        .first()
    )

    context = {
        "total_dispositivos": total_dispositivos,
        "total_ativos": total_ativos,
        "total_sessoes": total_sessoes,
        "total_leituras_brutas": total_leituras_brutas,
        "total_shots": total_shots,
        "ultima_sessao": ultima_sessao,
        "ultima_leitura_bruta": ultima_leitura_bruta,
        "ultimo_shot": ultimo_shot,
    }
    return render(request, "dispositivos/dashboard.html", context)


@login_required
def sessao_dispositivo_list(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    sessoes = obter_sessoes_qs(empresa_id).select_related("dispositivo", "empresa", "empregado", "furo").order_by("-iniciado_em")
    return render(request, "dispositivos/sessao_list.html", {
        "sessoes": sessoes,
    })


@login_required
def leitura_bruta_list(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    leituras = obter_leituras_qs(empresa_id).select_related("sessao", "empresa").order_by("-recebido_em")
    return render(request, "dispositivos/leitura_bruta_list.html", {
        "leituras": leituras,
    })


@login_required
def survey_shot_list(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    shots = obter_shots_qs(empresa_id).select_related("sessao", "empresa", "furo").order_by("-criado_em")
    return render(request, "dispositivos/survey_shot_list.html", {
        "shots": shots,
    })


@login_required
def dispositivo_list(request):
    """
    Lista todos os dispositivos registados no sistema.
    Futuramente pode ser filtrado por empresa, projeto, estado, tipo, etc.
    """
    empresa_id = _obter_empresa_id_utilizador(request)
    dispositivos = obter_dispositivos_qs(empresa_id).order_by("nome")

    context = {
        "dispositivos": dispositivos,
        "total_dispositivos": dispositivos.count(),
    }
    return render(request, "dispositivos/dispositivo_list.html", context)


@login_required
def sessao_dispositivo_detail(request, pk):
    empresa_id = _obter_empresa_id_utilizador(request)
    sessao = obter_sessao_detail(pk=pk, empresa_id=empresa_id)

    leituras_brutas = sessao.leituras_brutas.all().order_by("sequencia")
    leituras = sessao.leituras.all().order_by("timestamp_device", "criado_em")
    shots = sessao.shots.all().order_by("profundidade")

    context = {
        "sessao": sessao,
        "leituras_brutas": leituras_brutas,
        "leituras": leituras,
        "shots": shots,
    }
    return render(request, "dispositivos/sessao_detail.html", context)


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

    try:
        leitura = capturar_leitura_serial_para_sessao(sessao)
        messages.success(
            request,
            f"Leitura bruta capturada com sucesso. Sequência: {leitura.sequencia}"
        )
    except Exception as e:
        messages.error(request, f"Erro ao capturar leitura serial: {e}")

    return redirect("dispositivos:sessao_detail", pk=sessao.pk)

@login_required
def captura_dispositivo(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    empregado = obter_empregado_por_user_empresa(request.user, empresa_id=empresa_id)

    preview_data = request.session.get(MAGCRUISER_PREVIEW_SESSION_KEY)
    report_data = request.session.get(MAGCRUISER_REPORT_SESSION_KEY)
    preview_data = anexar_sessao_ao_preview(preview_data, empresa_id=empresa_id)
    try:
        historico_importacoes = list(
            listar_historico_importacoes_qs(empresa_id=empresa_id).order_by("-criado_em")[:20]
        )
    except ProgrammingError:
        historico_importacoes = []
        messages.warning(
            request,
            "Histórico de importações ainda não disponível nesta base de dados. "
            "Aplica as migrations da app Dispositivos.",
        )

    if request.method == "POST":
        action = (request.POST.get("action") or "create_session").strip()
        if action in {"preview_import", "save_import", "clear_import", "clear_import_report"}:
            try:
                resultado_acao = processar_acao_importacao_magcruiser(
                    action=action,
                    empresa_id=empresa_id,
                    request_post=request.POST,
                    request_files=request.FILES,
                    request_session=request.session,
                    utilizador=request.user,
                    preview_session_key=MAGCRUISER_PREVIEW_SESSION_KEY,
                    report_session_key=MAGCRUISER_REPORT_SESSION_KEY,
                )
                if resultado_acao.get("message_level") == "success":
                    messages.success(request, resultado_acao.get("message"))
                elif resultado_acao.get("message_level") == "info":
                    messages.info(request, resultado_acao.get("message"))
                elif resultado_acao.get("message_level") == "error":
                    messages.error(request, resultado_acao.get("message"))
            except Exception as exc:
                messages.error(request, f"Erro na ação de importação: {exc}")
            return redirect("dispositivos:captura")

        resultado = processar_criacao_sessao_captura(
            empresa_id=empresa_id,
            empregado=empregado,
            dispositivo_id=request.POST.get("dispositivo_id"),
            furo_id=request.POST.get("furo_id"),
        )
        if not resultado["ok"]:
            messages.error(request, resultado["erro"])
            return redirect("dispositivos:captura")

        sessao = resultado["sessao"]
        messages.success(request, "Sessão criada com sucesso.")
        return redirect("dispositivos:sessao_detail", pk=sessao.pk)

    contexto_base = construir_contexto_captura_dispositivo(empresa_id=empresa_id)
    return render(request, "dispositivos/captura.html", {
        **contexto_base,
        "magcruiser_preview": preview_data,
        "magcruiser_report": report_data,
        "historico_importacoes": historico_importacoes,
    })


@login_required
@require_GET
def importacao_historico_csv(request, pk):
    empresa_id = _obter_empresa_id_utilizador(request)
    historico = obter_historico_importacao(pk=pk, empresa_id=empresa_id)
    csv_content = render_historico_importacao_csv(historico)
    response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="importacao-magcruiser-{historico.pk}.csv"'
    return response
