# dispositivos/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from dispositivos.services.serial_service import capturar_leitura_serial_para_sessao
from dispositivos.models import (
    Dispositivo,
    SessaoDispositivo,
    LeituraBrutaDispositivo,
    SurveyShot,
)


from django.http import JsonResponse
import random
import time


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
def dispositivos_dashboard(request):
    total_dispositivos = Dispositivo.objects.count()
    total_ativos = Dispositivo.objects.filter(ativo=True).count()
    total_sessoes = SessaoDispositivo.objects.count()
    total_leituras_brutas = LeituraBrutaDispositivo.objects.count()
    total_shots = SurveyShot.objects.count()

    ultima_sessao = (
        SessaoDispositivo.objects.select_related("dispositivo", "empregado", "furo", "empresa")
        .order_by("-iniciado_em")
        .first()
    )

    ultima_leitura_bruta = (
        LeituraBrutaDispositivo.objects.select_related("sessao", "empresa")
        .order_by("-recebido_em")
        .first()
    )

    ultimo_shot = (
        SurveyShot.objects.select_related("sessao", "furo", "empresa")
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
    sessoes = (
        SessaoDispositivo.objects.select_related("dispositivo", "empresa", "empregado", "furo")
        .order_by("-iniciado_em")
    )
    return render(request, "dispositivos/sessao_list.html", {
        "sessoes": sessoes,
    })


@login_required
def leitura_bruta_list(request):
    leituras = (
        LeituraBrutaDispositivo.objects.select_related("sessao", "empresa")
        .order_by("-recebido_em")
    )
    return render(request, "dispositivos/leitura_bruta_list.html", {
        "leituras": leituras,
    })


@login_required
def survey_shot_list(request):
    shots = (
        SurveyShot.objects.select_related("sessao", "empresa", "furo")
        .order_by("-criado_em")
    )
    return render(request, "dispositivos/survey_shot_list.html", {
        "shots": shots,
    })


@login_required
def dispositivo_list(request):
    """
    Lista todos os dispositivos registados no sistema.
    Futuramente pode ser filtrado por empresa, projeto, estado, tipo, etc.
    """
    dispositivos = Dispositivo.objects.all().order_by("nome")

    context = {
        "dispositivos": dispositivos,
        "total_dispositivos": dispositivos.count(),
    }
    return render(request, "dispositivos/dispositivo_list.html", context)


@login_required
def sessao_dispositivo_detail(request, pk):
    sessao = get_object_or_404(
        SessaoDispositivo.objects.select_related(
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
    leitura = get_object_or_404(
        LeituraBrutaDispositivo.objects.select_related(
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
    sessao = get_object_or_404(
        SessaoDispositivo.objects.select_related("dispositivo", "empresa"),
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
    dispositivos = Dispositivo.objects.filter(ativo=True)

    return render(request, "dispositivos/captura.html", {
        "dispositivos": dispositivos,
    })