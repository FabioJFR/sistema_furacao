from geologia.forms import AnexoLogGeologicoForm, LogGeologicoFuroForm
from django.utils import timezone


def guardar_log_geologico_form(*, form):
    return form.save()


def guardar_anexo_log_form(*, form, log):
    anexo = form.save(commit=False)
    anexo.log = log
    anexo.empresa = log.empresa
    anexo.save()
    return anexo


def construir_form_log_create(*, request_post=None, request_files=None, furo, empresa):
    if request_post is not None:
        return LogGeologicoFuroForm(request_post, request_files, furo=furo, empresa=empresa)

    profundidade_atual = float(furo.profundidade_atual or 0.0)
    return LogGeologicoFuroForm(
        furo=furo,
        empresa=empresa,
        initial={
            "intervalo_de": profundidade_atual,
            "intervalo_ate": profundidade_atual,
        },
    )


def processar_log_create(*, request_post, request_files, furo, empresa):
    form = construir_form_log_create(
        request_post=request_post,
        request_files=request_files,
        furo=furo,
        empresa=empresa,
    )
    if form.is_valid():
        log = guardar_log_geologico_form(form=form)
        return {"ok": True, "form": form, "log": log}
    return {"ok": False, "form": form, "log": None}


def construir_form_log_update(*, request_post=None, request_files=None, log, empresa):
    if request_post is not None:
        return LogGeologicoFuroForm(
            request_post,
            request_files,
            instance=log,
            furo=log.furo,
            empresa=empresa,
        )
    return LogGeologicoFuroForm(instance=log, furo=log.furo, empresa=empresa)


def processar_log_update(*, request_post, request_files, log, empresa):
    form = construir_form_log_update(
        request_post=request_post,
        request_files=request_files,
        log=log,
        empresa=empresa,
    )
    if form.is_valid():
        log = guardar_log_geologico_form(form=form)
        if log.status_validacao != "pendente" or log.validado_por_id or log.validado_em:
            log.status_validacao = "pendente"
            log.validado_por = None
            log.validado_em = None
            log.observacao_validacao = ""
            log.save(update_fields=["status_validacao", "validado_por", "validado_em", "observacao_validacao", "atualizado_em"])
        return {"ok": True, "form": form, "log": log}
    return {"ok": False, "form": form, "log": log}


def construir_form_anexo_log(*, request_post=None, request_files=None):
    if request_post is not None:
        return AnexoLogGeologicoForm(request_post, request_files)
    return AnexoLogGeologicoForm()


def processar_anexo_log_create(*, request_post, request_files, log):
    form = construir_form_anexo_log(request_post=request_post, request_files=request_files)
    if form.is_valid():
        anexo = guardar_anexo_log_form(form=form, log=log)
        return {"ok": True, "form": form, "anexo": anexo}
    return {"ok": False, "form": form, "anexo": None}


def processar_fluxo_log_create(*, request_method, request_post, request_files, furo, empresa):
    if request_method == "POST":
        resultado = processar_log_create(
            request_post=request_post,
            request_files=request_files,
            furo=furo,
            empresa=empresa,
        )
        return {"form": resultado["form"], "resultado": resultado}

    return {
        "form": construir_form_log_create(furo=furo, empresa=empresa),
        "resultado": None,
    }


def processar_fluxo_log_update(*, request_method, request_post, request_files, log, empresa):
    if request_method == "POST":
        resultado = processar_log_update(
            request_post=request_post,
            request_files=request_files,
            log=log,
            empresa=empresa,
        )
        return {"form": resultado["form"], "resultado": resultado}

    return {
        "form": construir_form_log_update(log=log, empresa=empresa),
        "resultado": None,
    }


def processar_fluxo_anexo_log_create(*, request_method, request_post, request_files, log):
    if request_method == "POST":
        resultado = processar_anexo_log_create(
            request_post=request_post,
            request_files=request_files,
            log=log,
        )
        return {"form": resultado["form"], "resultado": resultado}

    return {
        "form": construir_form_anexo_log(),
        "resultado": None,
    }


def validar_log_geologico(*, log, user, acao, observacao=""):
    if acao not in {"aprovar", "rejeitar"}:
        return {"ok": False, "erro": "acao_invalida"}

    log.status_validacao = "aprovado" if acao == "aprovar" else "rejeitado"
    log.validado_por = user
    log.validado_em = timezone.now()
    log.observacao_validacao = (observacao or "").strip()
    log.save(update_fields=["status_validacao", "validado_por", "validado_em", "observacao_validacao", "atualizado_em"])
    return {"ok": True, "log": log}
