from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.permissions import admin_required
from geologia.forms import AnexoLogGeologicoForm, LogGeologicoFuroForm
from geologia.selectors_logs import (
    obter_anexos_log,
    obter_furo_log_geologico,
    obter_log_geologico,
)

from .common import obter_empresa_admin_geologia


@login_required
@admin_required
def log_geologico_create(request, furo_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furo = obter_furo_log_geologico(furo_id, empresa=empresa)

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

    log = obter_log_geologico(pk, empresa=empresa)
    anexos = obter_anexos_log(log)

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

    log = obter_log_geologico(pk, empresa=empresa)

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

    log = obter_log_geologico(pk, empresa=empresa)

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
