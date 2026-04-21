from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from core.permissions import admin_required
from geologia.models import LogGeologicoFuro, MissaoDroneFuro
from projetos.models import Furo

from .common import filtrar_queryset_por_empresa, obter_empresa_admin_geologia


@login_required
@admin_required
def geologia_hub(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furos_qs = filtrar_queryset_por_empresa(
        Furo.objects.select_related("projeto").order_by("projeto__nome", "nome"),
        empresa=empresa,
    )
    logs_qs = filtrar_queryset_por_empresa(
        LogGeologicoFuro.objects.select_related("furo", "furo__projeto").order_by("-data_registo", "-criado_em"),
        empresa=empresa,
    )
    missoes_qs = filtrar_queryset_por_empresa(
        MissaoDroneFuro.objects.select_related("furo", "furo__projeto").order_by("-data_voo", "-criado_em"),
        empresa=empresa,
    )

    return render(
        request,
        "geologia/hub.html",
        {
            "contexto_geologia": contexto_geologia,
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
def furo_geologia_dashboard(request, furo_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furos_qs = filtrar_queryset_por_empresa(Furo.objects.select_related("projeto"), empresa=empresa)
    furo = get_object_or_404(furos_qs, pk=furo_id)
    logs = (
        furo.logs_geologicos.select_related("medicao", "missao_drone")
        .prefetch_related("anexos")
        .order_by("intervalo_de", "intervalo_ate", "-criado_em")
    )
    missoes = furo.missoes_drone_geologia.all().order_by("-data_voo", "-criado_em")

    return render(
        request,
        "geologia/furo_dashboard.html",
        {
            "furo": furo,
            "logs": logs,
            "missoes": missoes,
        },
    )
