# dispositivos/views.py
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from dispositivos.services.serial_service import capturar_leitura_serial_para_sessao
from projetos.models import Empregados, Furo
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
    empregado = (
        Empregados.objects.filter(user=request.user)
        .select_related("empresa")
        .first()
    )
    if not empregado or not empregado.empresa_id:
        raise PermissionDenied("O utilizador autenticado não está associado a uma empresa.")
    return empregado.empresa_id


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
    empresa_id = _obter_empresa_id_utilizador(request)

    dispositivos_qs = Dispositivo.objects.filter(empresa_id=empresa_id)
    sessoes_qs = SessaoDispositivo.objects.filter(empresa_id=empresa_id)
    leituras_qs = LeituraBrutaDispositivo.objects.filter(empresa_id=empresa_id)
    shots_qs = SurveyShot.objects.filter(empresa_id=empresa_id)

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
    sessoes = (
        SessaoDispositivo.objects.filter(empresa_id=empresa_id)
        .select_related("dispositivo", "empresa", "empregado", "furo")
        .order_by("-iniciado_em")
    )
    return render(request, "dispositivos/sessao_list.html", {
        "sessoes": sessoes,
    })


@login_required
def leitura_bruta_list(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    leituras = (
        LeituraBrutaDispositivo.objects.filter(empresa_id=empresa_id)
        .select_related("sessao", "empresa")
        .order_by("-recebido_em")
    )
    return render(request, "dispositivos/leitura_bruta_list.html", {
        "leituras": leituras,
    })


@login_required
def survey_shot_list(request):
    empresa_id = _obter_empresa_id_utilizador(request)
    shots = (
        SurveyShot.objects.filter(empresa_id=empresa_id)
        .select_related("sessao", "empresa", "furo")
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
    empresa_id = _obter_empresa_id_utilizador(request)
    dispositivos = Dispositivo.objects.filter(empresa_id=empresa_id).order_by("nome")

    context = {
        "dispositivos": dispositivos,
        "total_dispositivos": dispositivos.count(),
    }
    return render(request, "dispositivos/dispositivo_list.html", context)


@login_required
def sessao_dispositivo_detail(request, pk):
    empresa_id = _obter_empresa_id_utilizador(request)
    sessao = get_object_or_404(
        SessaoDispositivo.objects.filter(empresa_id=empresa_id).select_related(
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
    leitura = get_object_or_404(
        LeituraBrutaDispositivo.objects.filter(empresa_id=empresa_id).select_related(
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
    sessao = get_object_or_404(
        SessaoDispositivo.objects.filter(empresa_id=empresa_id).select_related("dispositivo", "empresa"),
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
    empregado = (
        Empregados.objects.filter(user=request.user, empresa_id=empresa_id)
        .select_related("empresa")
        .first()
    )

    dispositivos = Dispositivo.objects.filter(empresa_id=empresa_id, ativo=True).order_by("nome")
    furos = Furo.objects.filter(empresa_id=empresa_id).select_related("projeto").order_by("nome")
    sessoes_ativas = (
        SessaoDispositivo.objects.filter(empresa_id=empresa_id, status__in=["criada", "ligando", "ligado"])
        .select_related("dispositivo", "furo", "empregado")
        .order_by("-iniciado_em")
    )
    sessoes_recentes = (
        SessaoDispositivo.objects.filter(empresa_id=empresa_id)
        .select_related("dispositivo", "furo", "empregado")
        .order_by("-iniciado_em")[:10]
    )

    if request.method == "POST":
        dispositivo_id = request.POST.get("dispositivo_id")
        furo_id = request.POST.get("furo_id")

        if not dispositivo_id or not furo_id:
            messages.error(request, "Selecione um dispositivo e um furo para iniciar a sessão.")
            return redirect("dispositivos:captura")

        dispositivo = get_object_or_404(
            Dispositivo.objects.filter(empresa_id=empresa_id, ativo=True),
            pk=dispositivo_id,
        )
        furo = get_object_or_404(
            Furo.objects.filter(empresa_id=empresa_id),
            pk=furo_id,
        )

        sessao = SessaoDispositivo.objects.create(
            dispositivo=dispositivo,
            empresa_id=empresa_id,
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
