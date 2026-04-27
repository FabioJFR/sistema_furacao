def guardar_log_geologico_form(*, form):
    return form.save()


def guardar_anexo_log_form(*, form, log):
    anexo = form.save(commit=False)
    anexo.log = log
    anexo.empresa = log.empresa
    anexo.save()
    return anexo
