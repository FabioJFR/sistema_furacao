from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from dispositivos.models import (
    Dispositivo,
    SessaoDispositivo,
    LeituraBrutaDispositivo,
    SurveyShot,
)


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
def dispositivo_list(request):
    dispositivos = Dispositivo.objects.select_related("empresa").order_by("nome")
    return render(request, "dispositivos/dispositivo_list.html", {
        "dispositivos": dispositivos,
    })


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