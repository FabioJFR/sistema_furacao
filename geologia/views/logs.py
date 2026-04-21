from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions import admin_required
from geologia.forms import AnexoLogGeologicoForm, LogGeologicoFuroForm
from geologia.models import LogGeologicoFuro
from projetos.models import Furo

from .common import filtrar_queryset_por_empresa, obter_empresa_admin_geologia


@login_required
@admin_required
def log_geologico_create(request, furo_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furo = get_object_or_404(
        filtrar_queryset_por_empresa(Furo.objects.select_related("projeto"), empresa=empresa),
        pk=furo_id,
    )

    if request.method == "POST":
        form = LogGeologicoFuroForm(request.POST, request.FILES, furo=furo, empresa=empresa)
        if form.is_valid():
            log = form.save()
            messages.success(request, "Log geologico registado com sucesso.")
            return redirect("geologia:log_detail", pk=log.pk)
        messages.error(request, "Nao foi possivel guardar o log geologico.")
    else:
        profundidade_atual = float(furo.profundidade_atual or 0.0)
        form = LogGeologicoFuroForm(
            furo=furo,
            empresa=empresa,
            initial={
                "intervalo_de": profundidade_atual,
                "intervalo_ate": profundidade_atual,
            },
        )

    return render(
        request,
        "geologia/log_form.html",
        {
            "form": form,
            "furo": furo,
            "titulo": f"Novo Log Geologico - {furo.nome}",
        },
    )


@login_required
@admin_required
def log_geologico_detail(request, pk):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    logs_qs = filtrar_queryset_por_empresa(
        LogGeologicoFuro.objects.select_related("furo", "furo__projeto", "medicao", "missao_drone"),
        empresa=empresa,
    )
    log = get_object_or_404(logs_qs, pk=pk)
    anexos = log.anexos.all().order_by("-criado_em")

    return render(
        request,
        "geologia/log_detail.html",
        {
            "log": log,
            "furo": log.furo,
            "anexos": anexos,
        },
    )


@login_required
@admin_required
def log_geologico_update(request, pk):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    log = get_object_or_404(filtrar_queryset_por_empresa(LogGeologicoFuro.objects.all(), empresa=empresa), pk=pk)

    if request.method == "POST":
        form = LogGeologicoFuroForm(
            request.POST,
            request.FILES,
            instance=log,
            furo=log.furo,
            empresa=empresa,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Log geologico atualizado com sucesso.")
            return redirect("geologia:log_detail", pk=log.pk)
        messages.error(request, "Nao foi possivel atualizar o log geologico.")
    else:
        form = LogGeologicoFuroForm(instance=log, furo=log.furo, empresa=empresa)

    return render(
        request,
        "geologia/log_form.html",
        {
            "form": form,
            "furo": log.furo,
            "titulo": f"Editar Log Geologico - {log.furo.nome}",
            "log": log,
        },
    )


@login_required
@admin_required
def anexo_log_create(request, pk):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    log = get_object_or_404(filtrar_queryset_por_empresa(LogGeologicoFuro.objects.all(), empresa=empresa), pk=pk)

    if request.method == "POST":
        form = AnexoLogGeologicoForm(request.POST, request.FILES)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.log = log
            anexo.empresa = log.empresa
            anexo.save()
            messages.success(request, "Anexo adicionado com sucesso.")
            return redirect("geologia:log_detail", pk=log.pk)
        messages.error(request, "Nao foi possivel adicionar o anexo.")
    else:
        form = AnexoLogGeologicoForm()

    return render(
        request,
        "geologia/anexo_form.html",
        {
            "form": form,
            "log": log,
            "furo": log.furo,
            "titulo": f"Novo Anexo - {log.titulo}",
        },
    )
