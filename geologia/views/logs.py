from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from core.permissions import admin_required
from geologia.selectors.logs import (
    obter_anexos_log,
    obter_furo_log_geologico,
    obter_log_geologico,
)
from geologia.services.logs import (
    processar_fluxo_anexo_log_create,
    processar_fluxo_log_create,
    processar_fluxo_log_update,
)

from .common import obter_empresa_admin_geologia


def _processar_post_form(
    *,
    request,
    resultado,
    mensagem_sucesso,
    mensagem_erro,
    redirect_name,
    redirect_kwargs,
):
    if request.method != "POST":
        return None
    if resultado.get("ok"):
        messages.success(request, mensagem_sucesso)
        return redirect(redirect_name, **redirect_kwargs)
    messages.error(request, mensagem_erro)
    return None


@login_required
@admin_required
def log_geologico_create(request, furo_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    furo = obter_furo_log_geologico(furo_id, empresa=empresa)

    fluxo = processar_fluxo_log_create(
        request_method=request.method,
        request_post=request.POST,
        request_files=request.FILES,
        furo=furo,
        empresa=empresa,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta_post = _processar_post_form(
            request=request,
            resultado=resultado,
            mensagem_sucesso=_("Log geológico registado com sucesso."),
            mensagem_erro=_("Não foi possível guardar o log geológico."),
            redirect_name="geologia:log_detail",
            redirect_kwargs={"pk": resultado["log"].pk} if resultado.get("ok") else {},
        )
        if resposta_post:
            return resposta_post

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

    fluxo = processar_fluxo_log_update(
        request_method=request.method,
        request_post=request.POST,
        request_files=request.FILES,
        log=log,
        empresa=empresa,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta_post = _processar_post_form(
            request=request,
            resultado=resultado,
            mensagem_sucesso=_("Log geológico atualizado com sucesso."),
            mensagem_erro=_("Não foi possível atualizar o log geológico."),
            redirect_name="geologia:log_detail",
            redirect_kwargs={"pk": log.pk},
        )
        if resposta_post:
            return resposta_post

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

    fluxo = processar_fluxo_anexo_log_create(
        request_method=request.method,
        request_post=request.POST,
        request_files=request.FILES,
        log=log,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta_post = _processar_post_form(
            request=request,
            resultado=resultado,
            mensagem_sucesso=_("Anexo adicionado com sucesso."),
            mensagem_erro=_("Não foi possível adicionar o anexo."),
            redirect_name="geologia:log_detail",
            redirect_kwargs={"pk": log.pk},
        )
        if resposta_post:
            return resposta_post

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
