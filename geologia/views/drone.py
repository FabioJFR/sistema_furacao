from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions import admin_required
from geologia.forms import ImportarMissaoDroneForm, MissaoDroneFuroForm
from geologia.models import MissaoDroneFuro
from projetos.models import Furo

from .common import filtrar_queryset_por_empresa, obter_empresa_admin_geologia


@login_required
@admin_required
def drone_hub(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furos_qs = filtrar_queryset_por_empresa(
        Furo.objects.select_related("projeto").order_by("projeto__nome", "nome"),
        empresa=empresa,
    )
    missoes_qs = filtrar_queryset_por_empresa(
        MissaoDroneFuro.objects.select_related("furo", "furo__projeto").order_by("-data_voo", "-criado_em"),
        empresa=empresa,
    )
    furos = list(furos_qs[:12])
    missoes_recentes = list(missoes_qs[:8])

    if request.method == "POST":
        form = ImportarMissaoDroneForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            missao = form.save()
            messages.success(request, "Missao DJI importada com sucesso.")
            return redirect("geologia:missao_detail", pk=missao.pk)
        messages.error(request, "Nao foi possivel importar a missao DJI.")
    else:
        form = ImportarMissaoDroneForm(empresa=empresa)

    context = {
        "form": form,
        "furos": furos,
        "missoes_recentes": missoes_recentes,
        "total_furos": furos_qs.count(),
        "total_missoes": missoes_qs.count(),
        "total_importadas": missoes_qs.filter(status="importada").count(),
    }
    return render(request, "geologia/drone_hub.html", context)


@login_required
@admin_required
def missao_drone_create(request, furo_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furos_qs = filtrar_queryset_por_empresa(Furo.objects.select_related("projeto"), empresa=empresa)
    furo = get_object_or_404(furos_qs, pk=furo_id)

    if request.method == "POST":
        form = MissaoDroneFuroForm(request.POST, request.FILES, furo=furo, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, "Missao do drone registada com sucesso.")
            return redirect("geologia:furo_dashboard", furo_id=furo.pk)
        messages.error(request, "Nao foi possivel guardar a missao do drone.")
    else:
        form = MissaoDroneFuroForm(furo=furo, empresa=empresa, initial={"titulo": f"Levantamento DJI Mini 4 Pro - {furo.nome}"})

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

    missoes_qs = filtrar_queryset_por_empresa(
        MissaoDroneFuro.objects.select_related("furo", "furo__projeto"),
        empresa=empresa,
    )
    missao = get_object_or_404(missoes_qs, pk=pk)
    logs_relacionados = missao.logs_geologicos.select_related("furo").order_by("intervalo_de", "intervalo_ate")

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

    missao = get_object_or_404(filtrar_queryset_por_empresa(MissaoDroneFuro.objects.all(), empresa=empresa), pk=pk)

    if request.method == "POST":
        form = MissaoDroneFuroForm(
            request.POST,
            request.FILES,
            instance=missao,
            furo=missao.furo,
            empresa=empresa,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Missao do drone atualizada com sucesso.")
            return redirect("geologia:missao_detail", pk=missao.pk)
        messages.error(request, "Nao foi possivel atualizar a missao do drone.")
    else:
        form = MissaoDroneFuroForm(instance=missao, furo=missao.furo, empresa=empresa)

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
