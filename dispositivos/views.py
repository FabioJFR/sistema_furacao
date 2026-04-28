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
    obter_dispositivo_ativo,
    obter_dispositivos_qs,
    obter_empregado_por_user_empresa,
    obter_furo,
    obter_furos_qs,
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


from django.http import JsonResponse
import random
import time


def _obter_empresa_id_utilizador(request):
    if request.user.is_superuser:
        return None
    raise PermissionDenied("A área de dispositivos está disponível apenas para administradores.")


def _garantir_admin_api(request):
    if not request.user.is_authenticated:
        raise PermissionDenied("Autenticação obrigatória.")
    if not request.user.is_superuser:
        raise PermissionDenied("A área de dispositivos está disponível apenas para administradores.")


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

    return JsonResponse({
        "ok": True,
        "eventos": eventos,
        "portas": portas,
    })


@login_required
@require_GET
def api_procurar_dispositivos_bluetooth(request):
    _garantir_admin_api(request)
    resultado = processar_procura_dispositivos_bluetooth()
    return JsonResponse(
        {
            "ok": resultado["ok"],
            "eventos": resultado["eventos"],
            "dispositivos": resultado["dispositivos"],
        },
        status=200 if resultado["ok"] else resultado.get("status", 400),
    )


@login_required
@require_POST
def api_testar_leitura_usb(request):
    _garantir_admin_api(request)
    resultado = processar_teste_leitura_usb(dispositivo_id=request.POST.get("dispositivo_id"))
    if resultado["ok"]:
        return JsonResponse(
            {
                "ok": True,
                "eventos": resultado["eventos"],
                "leitura": resultado["leitura"],
            }
        )
    return JsonResponse(
        {
            "ok": False,
            "eventos": resultado["eventos"],
        },
        status=resultado.get("status", 400),
    )


@login_required
@require_POST
def api_inspecionar_dispositivo_bluetooth(request):
    _garantir_admin_api(request)

    address = (request.POST.get("address") or "").strip()
    name = (request.POST.get("name") or "").strip()
    resultado = processar_inspecao_bluetooth_detectado(address=address, name=name)
    if resultado["ok"]:
        return JsonResponse(
            {
                "ok": True,
                "eventos": resultado["eventos"],
                "inspecao": resultado["inspecao"],
            }
        )
    return JsonResponse(
        {
            "ok": False,
            "eventos": resultado["eventos"],
        },
        status=resultado.get("status", 400),
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
            return JsonResponse(
                {
                    "ok": False,
                    "eventos": [{"tipo": "erro", "mensagem": resultado["erro"]}],
                },
                status=resultado.get("status", 400),
            )
        dispositivo = resultado["dispositivo"]
        eventos = resultado["eventos"]

        return JsonResponse(
            {
                "ok": True,
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
        return JsonResponse(
            {
                "ok": False,
                "eventos": [{"tipo": "erro", "mensagem": f"Não foi possível guardar o dispositivo: {exc}"}],
            },
            status=400,
        )


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
            "ok": True,
            "eventos": resultado["eventos"],
            "modo": resultado["modo"],
        }
        if resultado.get("leitura") is not None:
            response["leitura"] = resultado["leitura"]
        if resultado.get("inspecao") is not None:
            response["inspecao"] = resultado["inspecao"]
        return JsonResponse(response)
    return JsonResponse(
        {
            "ok": False,
            "eventos": resultado["eventos"],
        },
        status=resultado.get("status", 400),
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

    dispositivos = obter_dispositivos_qs(empresa_id).filter(ativo=True)
    furos = obter_furos_qs(empresa_id).select_related("projeto")
    sessoes_ativas = obter_sessoes_qs(empresa_id).filter(status__in=["criada", "ligando", "ligado"])
    sessoes_recentes = obter_sessoes_qs(empresa_id)

    dispositivos = dispositivos.order_by("nome")
    furos = furos.order_by("nome")
    sessoes_ativas = sessoes_ativas.select_related("dispositivo", "furo", "empregado").order_by("-iniciado_em")
    sessoes_recentes = sessoes_recentes.select_related("dispositivo", "furo", "empregado").order_by("-iniciado_em")[:10]

    if request.method == "POST":
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

    return render(request, "dispositivos/captura.html", {
        "dispositivos": dispositivos,
        "furos": furos,
        "sessoes_ativas": sessoes_ativas,
        "sessoes_recentes": sessoes_recentes,
    })
