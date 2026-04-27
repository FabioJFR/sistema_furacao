from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from core.permissions import admin_required
from geologia.forms import AnexoLogGeologicoForm, LogGeologicoFuroForm
from geologia.selectors.logs import (
    obter_anexos_log,
    obter_furo_log_geologico,
    obter_log_geologico,
)
from geologia.services.logs import guardar_anexo_log_form, guardar_log_geologico_form

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
            log = guardar_log_geologico_form(form=form)
            messages.success(request, _("Log geológico registado com sucesso."))
            return redirect("geologia:log_detail", pk=log.pk)
        messages.error(request, _("Não foi possível guardar o log geológico."))
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
            "titulo": _("Novo Log Geológico - %(nome)s") % {"nome": furo.nome},
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
            guardar_log_geologico_form(form=form)
            messages.success(request, _("Log geológico atualizado com sucesso."))
            return redirect("geologia:log_detail", pk=log.pk)
        messages.error(request, _("Não foi possível atualizar o log geológico."))
    else:
        form = LogGeologicoFuroForm(instance=log, furo=log.furo, empresa=empresa)

    return render(
        request,
        "geologia/log_form.html",
        {
            "form": form,
            "furo": log.furo,
            "titulo": _("Editar Log Geológico - %(nome)s") % {"nome": log.furo.nome},
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
            guardar_anexo_log_form(form=form, log=log)
            messages.success(request, _("Anexo adicionado com sucesso."))
            return redirect("geologia:log_detail", pk=log.pk)
        messages.error(request, _("Não foi possível adicionar o anexo."))
    else:
        form = AnexoLogGeologicoForm()

    return render(
        request,
        "geologia/anexo_form.html",
        {
            "form": form,
            "log": log,
            "furo": log.furo,
            "titulo": _("Novo Anexo - %(titulo)s") % {"titulo": log.titulo},
        },
    )
