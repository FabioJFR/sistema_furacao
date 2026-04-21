# dispositivos/views.py
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from dispositivos.services.serial_service import (
    capturar_leitura_serial_para_sessao,
    capturar_preview_serial_da_porta,
    capturar_preview_serial_do_dispositivo,
    inspecionar_dispositivo_bluetooth,
    listar_dispositivos_bluetooth,
    listar_portas_seriais,
)
from projetos.models import Empregados, Furo
from plataforma.models import Empresa
from dispositivos.models import (
    Dispositivo,
    SessaoDispositivo,
    LeituraBrutaDispositivo,
    SurveyShot,
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
    if furo_id:
        furo = get_object_or_404(Furo.objects.select_related("empresa", "projeto__empresa"), pk=furo_id)
        empresa = furo.empresa or getattr(furo.projeto, "empresa", None)
        if empresa:
            return empresa

    empresas = Empresa.objects.filter(ativo=True).order_by("nome")
    if empresas.count() == 1:
        return empresas.first()

    raise ValueError("Selecione um furo com empresa associada para guardar o dispositivo.")


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

    try:
        dispositivos = listar_dispositivos_bluetooth()
        candidatos = sum(
            1 for dispositivo in dispositivos
            if dispositivo.get("tipo_detectado") == "candidato_medicao"
        )
        eventos = [
            {"tipo": "info", "mensagem": "A procurar dispositivos Bluetooth visíveis..."},
            {"tipo": "info", "mensagem": f"Foram encontrados {len(dispositivos)} dispositivos Bluetooth."},
        ]
        if candidatos:
            eventos.append(
                {
                    "tipo": "sucesso",
                    "mensagem": f"Foram identificados {candidatos} candidatos a aparelho de medidas.",
                }
            )
        else:
            eventos.append(
                {
                    "tipo": "info",
                    "mensagem": "Nenhum dispositivo foi identificado como candidato claro a aparelho de medidas.",
                }
            )
        return JsonResponse(
            {
                "ok": True,
                "eventos": eventos,
                "dispositivos": dispositivos,
            }
        )
    except Exception as exc:
        return JsonResponse(
            {
                "ok": False,
                "eventos": [
                    {"tipo": "erro", "mensagem": f"Erro ao procurar dispositivos Bluetooth: {exc}"}
                ],
                "dispositivos": [],
            },
            status=400,
        )


@login_required
@require_POST
def api_testar_leitura_usb(request):
    _garantir_admin_api(request)

    dispositivo_id = request.POST.get("dispositivo_id")
    if not dispositivo_id:
        return JsonResponse(
            {
                "ok": False,
                "eventos": [
                    {"tipo": "erro", "mensagem": "Selecione um dispositivo antes de testar a leitura."}
                ],
            },
            status=400,
        )

    dispositivo = get_object_or_404(Dispositivo.objects.filter(ativo=True), pk=dispositivo_id)

    eventos = [
        {"tipo": "info", "mensagem": f"Dispositivo selecionado: {dispositivo.nome}."},
        {"tipo": "info", "mensagem": "A validar configuração USB/Serial..."},
    ]

    try:
        eventos.append(
            {
                "tipo": "info",
                "mensagem": f"A ligar à porta {dispositivo.porta or '-'} com baudrate {dispositivo.baudrate}.",
            }
        )
        eventos.append(
            {
                "tipo": "info",
                "mensagem": "Ligado. A procurar dados enviados pelo aparelho...",
            }
        )

        leitura = capturar_preview_serial_do_dispositivo(dispositivo)

        eventos.append(
            {
                "tipo": "sucesso",
                "mensagem": f"Dados recebidos com sucesso. Total de bytes: {leitura['total_bytes']}.",
            }
        )

        return JsonResponse(
            {
                "ok": True,
                "eventos": eventos,
                "leitura": leitura,
            }
        )
    except Exception as exc:
        eventos.append(
            {
                "tipo": "erro",
                "mensagem": f"Erro durante a leitura: {exc}",
            }
        )
        return JsonResponse(
            {
                "ok": False,
                "eventos": eventos,
            },
            status=400,
        )


@login_required
@require_POST
def api_inspecionar_dispositivo_bluetooth(request):
    _garantir_admin_api(request)

    address = (request.POST.get("address") or "").strip()
    name = (request.POST.get("name") or "").strip()

    if not address:
        return JsonResponse(
            {
                "ok": False,
                "eventos": [
                    {"tipo": "erro", "mensagem": "É necessário indicar o endereço Bluetooth para inspeção."}
                ],
            },
            status=400,
        )

    eventos = [
        {"tipo": "info", "mensagem": f"A preparar inspeção Bluetooth para {name or address}."},
        {"tipo": "info", "mensagem": "A tentar ligar ao dispositivo para recolher serviços BLE..."},
    ]

    try:
        inspecao = inspecionar_dispositivo_bluetooth(address)
        total_services = len(inspecao.get("services") or [])
        total_characteristics = sum(
            len(service.get("characteristics") or [])
            for service in inspecao.get("services") or []
        )
        eventos.append(
            {
                "tipo": "sucesso",
                "mensagem": (
                    f"Inspeção concluída. Serviços: {total_services}. "
                    f"Características: {total_characteristics}."
                ),
            }
        )

        return JsonResponse(
            {
                "ok": True,
                "eventos": eventos,
                "inspecao": inspecao,
            }
        )
    except Exception as exc:
        eventos.append(
            {
                "tipo": "erro",
                "mensagem": f"Não foi possível inspecionar o dispositivo Bluetooth: {exc}",
            }
        )
        return JsonResponse(
            {
                "ok": False,
                "eventos": eventos,
            },
            status=400,
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

    if canal not in {"usb_serial", "bluetooth"}:
        return JsonResponse(
            {
                "ok": False,
                "eventos": [{"tipo": "erro", "mensagem": "Canal do dispositivo não suportado para registo."}],
            },
            status=400,
        )

    if not identificador:
        return JsonResponse(
            {
                "ok": False,
                "eventos": [{"tipo": "erro", "mensagem": "Falta o identificador físico do dispositivo encontrado."}],
            },
            status=400,
        )

    try:
        empresa = _resolver_empresa_para_registo(request)
        defaults = {
            "empresa": empresa,
            "nome": nome[:120],
            "tipo": "magcruiser",
            "canal": canal,
            "numero_serie": "",
            "identificador_fisico": identificador[:120],
            "ativo": True,
        }
        if canal == "usb_serial":
            defaults["porta"] = identificador[:120]
            defaults["baudrate"] = baudrate
            dispositivo, created = Dispositivo.objects.update_or_create(
                empresa=empresa,
                porta=identificador[:120],
                defaults=defaults,
            )
        else:
            defaults["mac_address"] = identificador[:120]
            dispositivo, created = Dispositivo.objects.update_or_create(
                empresa=empresa,
                mac_address=identificador[:120],
                defaults=defaults,
            )

        eventos = [
            {"tipo": "sucesso", "mensagem": f"Dispositivo {'criado' if created else 'atualizado'} com sucesso."},
            {"tipo": "info", "mensagem": f"Empresa associada: {empresa}."},
        ]
        if descricao:
            eventos.append({"tipo": "info", "mensagem": f"Descrição detetada: {descricao}."})

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

    if canal == "usb_serial":
        if not identificador:
            return JsonResponse(
                {
                    "ok": False,
                    "eventos": [{"tipo": "erro", "mensagem": "É necessário indicar a porta USB/Serial."}],
                },
                status=400,
            )

        eventos = [
            {"tipo": "info", "mensagem": f"A escutar a porta {identificador} do dispositivo {nome}."},
            {"tipo": "info", "mensagem": "A procurar bytes enviados pelo aparelho..."},
        ]
        try:
            leitura = capturar_preview_serial_da_porta(identificador, baudrate=baudrate)
            eventos.append(
                {
                    "tipo": "sucesso",
                    "mensagem": f"Foram recebidos {leitura['total_bytes']} bytes pela porta serial.",
                }
            )
            if leitura.get("parece_csv"):
                eventos.append(
                    {
                        "tipo": "sucesso",
                        "mensagem": "O conteúdo recebido parece estar em formato CSV.",
                    }
                )
            return JsonResponse(
                {
                    "ok": True,
                    "eventos": eventos,
                    "leitura": leitura,
                    "modo": "usb_serial",
                }
            )
        except Exception as exc:
            eventos.append({"tipo": "erro", "mensagem": f"Erro ao escutar a porta serial: {exc}"})
            return JsonResponse({"ok": False, "eventos": eventos}, status=400)

    if canal == "bluetooth":
        if not identificador:
            return JsonResponse(
                {
                    "ok": False,
                    "eventos": [{"tipo": "erro", "mensagem": "É necessário indicar o endereço Bluetooth."}],
                },
                status=400,
            )
        eventos = [
            {"tipo": "info", "mensagem": f"A tentar escutar o dispositivo Bluetooth {nome}."},
            {"tipo": "info", "mensagem": "A recolher serviços e características BLE disponíveis..."},
        ]
        try:
            inspecao = inspecionar_dispositivo_bluetooth(identificador)
            total_services = len(inspecao.get("services") or [])
            eventos.append(
                {
                    "tipo": "sucesso",
                    "mensagem": f"Foram encontrados {total_services} serviços BLE durante a escuta.",
                }
            )
            eventos.append(
                {
                    "tipo": "info",
                    "mensagem": "A escuta Bluetooth genérica mostra metadados e serviços; streaming contínuo depende do protocolo do aparelho.",
                }
            )
            return JsonResponse(
                {
                    "ok": True,
                    "eventos": eventos,
                    "inspecao": inspecao,
                    "modo": "bluetooth",
                }
            )
        except Exception as exc:
            eventos.append({"tipo": "erro", "mensagem": f"Erro ao escutar Bluetooth: {exc}"})
            return JsonResponse({"ok": False, "eventos": eventos}, status=400)

    return JsonResponse(
        {
            "ok": False,
            "eventos": [{"tipo": "erro", "mensagem": "Canal não suportado para escuta."}],
        },
        status=400,
    )

@login_required
def dispositivos_dashboard(request):
    empresa_id = _obter_empresa_id_utilizador(request)

    dispositivos_qs = Dispositivo.objects.all()
    sessoes_qs = SessaoDispositivo.objects.all()
    leituras_qs = LeituraBrutaDispositivo.objects.all()
    shots_qs = SurveyShot.objects.all()

    if empresa_id:
        dispositivos_qs = dispositivos_qs.filter(empresa_id=empresa_id)
        sessoes_qs = sessoes_qs.filter(empresa_id=empresa_id)
        leituras_qs = leituras_qs.filter(empresa_id=empresa_id)
        shots_qs = shots_qs.filter(empresa_id=empresa_id)

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
    sessoes = SessaoDispositivo.objects.all()
    if empresa_id:
        sessoes = sessoes.filter(empresa_id=empresa_id)
    sessoes = sessoes.select_related("dispositivo", "empresa", "empregado", "furo").order_by("-iniciado_em")
    return render(request, "dispositivos/sessao_list.html", {
        "sessoes": sessoes,
    })


@login_required
def leitura_bruta_list(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    leituras = LeituraBrutaDispositivo.objects.all()
    if empresa_id:
        leituras = leituras.filter(empresa_id=empresa_id)
    leituras = leituras.select_related("sessao", "empresa").order_by("-recebido_em")
    return render(request, "dispositivos/leitura_bruta_list.html", {
        "leituras": leituras,
    })


@login_required
def survey_shot_list(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    shots = SurveyShot.objects.all()
    if empresa_id:
        shots = shots.filter(empresa_id=empresa_id)
    shots = shots.select_related("sessao", "empresa", "furo").order_by("-criado_em")
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
    dispositivos = Dispositivo.objects.all()
    if empresa_id:
        dispositivos = dispositivos.filter(empresa_id=empresa_id)
    dispositivos = dispositivos.order_by("nome")

    context = {
        "dispositivos": dispositivos,
        "total_dispositivos": dispositivos.count(),
    }
    return render(request, "dispositivos/dispositivo_list.html", context)


@login_required
def sessao_dispositivo_detail(request, pk):
    empresa_id = _obter_empresa_id_utilizador(request)
    sessao_qs = SessaoDispositivo.objects.all()
    if empresa_id:
        sessao_qs = sessao_qs.filter(empresa_id=empresa_id)
    sessao = get_object_or_404(
        sessao_qs.select_related(
            "dispositivo", "empresa", "empregado", "furo"
        ),
        pk=pk,
    )

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
    leituras_qs = LeituraBrutaDispositivo.objects.all()
    if empresa_id:
        leituras_qs = leituras_qs.filter(empresa_id=empresa_id)
    leitura = get_object_or_404(
        leituras_qs.select_related(
            "sessao", "empresa", "sessao__dispositivo", "sessao__furo", "sessao__empregado"
        ),
        pk=pk,
    )

    context = {
        "leitura": leitura,
    }
    return render(request, "dispositivos/leitura_bruta_detail.html", context)


@login_required
@require_POST
def capturar_leitura_serial_view(request, pk):
    empresa_id = _obter_empresa_id_utilizador(request)
    sessao_qs = SessaoDispositivo.objects.all()
    if empresa_id:
        sessao_qs = sessao_qs.filter(empresa_id=empresa_id)
    sessao = get_object_or_404(
        sessao_qs.select_related("dispositivo", "empresa"),
        pk=pk,
    )

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
    empregado = None
    if empresa_id:
        empregado = (
            Empregados.objects.filter(user=request.user, empresa_id=empresa_id)
            .select_related("empresa")
            .first()
        )

    dispositivos = Dispositivo.objects.filter(ativo=True)
    furos = Furo.objects.all().select_related("projeto")
    sessoes_ativas = SessaoDispositivo.objects.filter(status__in=["criada", "ligando", "ligado"])
    sessoes_recentes = SessaoDispositivo.objects.all()

    if empresa_id:
        dispositivos = dispositivos.filter(empresa_id=empresa_id)
        furos = furos.filter(empresa_id=empresa_id)
        sessoes_ativas = sessoes_ativas.filter(empresa_id=empresa_id)
        sessoes_recentes = sessoes_recentes.filter(empresa_id=empresa_id)

    dispositivos = dispositivos.order_by("nome")
    furos = furos.order_by("nome")
    sessoes_ativas = sessoes_ativas.select_related("dispositivo", "furo", "empregado").order_by("-iniciado_em")
    sessoes_recentes = sessoes_recentes.select_related("dispositivo", "furo", "empregado").order_by("-iniciado_em")[:10]

    if request.method == "POST":
        dispositivo_id = request.POST.get("dispositivo_id")
        furo_id = request.POST.get("furo_id")

        if not dispositivo_id or not furo_id:
            messages.error(request, "Selecione um dispositivo e um furo para iniciar a sessão.")
            return redirect("dispositivos:captura")

        dispositivo_qs = Dispositivo.objects.filter(ativo=True)
        furo_qs = Furo.objects.all()
        if empresa_id:
            dispositivo_qs = dispositivo_qs.filter(empresa_id=empresa_id)
            furo_qs = furo_qs.filter(empresa_id=empresa_id)

        dispositivo = get_object_or_404(dispositivo_qs, pk=dispositivo_id)
        furo = get_object_or_404(furo_qs, pk=furo_id)

        if dispositivo.empresa_id != furo.empresa_id:
            messages.error(request, "O dispositivo e o furo têm de pertencer à mesma empresa.")
            return redirect("dispositivos:captura")

        sessao = SessaoDispositivo.objects.create(
            dispositivo=dispositivo,
            empresa=dispositivo.empresa,
            empregado=empregado,
            furo=furo,
            status="criada",
        )

        messages.success(request, "Sessão criada com sucesso.")
        return redirect("dispositivos:sessao_detail", pk=sessao.pk)

    return render(request, "dispositivos/captura.html", {
        "dispositivos": dispositivos,
        "furos": furos,
        "sessoes_ativas": sessoes_ativas,
        "sessoes_recentes": sessoes_recentes,
    })
