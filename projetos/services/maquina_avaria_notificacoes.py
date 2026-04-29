from django.conf import settings
from django.core.mail import send_mail


BACKENDS_SEM_ENTREGA_REAL = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
}


def _resolver_from_email():
    backend = (getattr(settings, "EMAIL_BACKEND", "") or "").strip()
    email_host_user = (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
    default_from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
    if backend == "django.core.mail.backends.smtp.EmailBackend" and email_host_user:
        return email_host_user
    return default_from_email or email_host_user or "noreply@sistemafuracao.local"


def _email_empregado(empregado):
    if not empregado:
        return ""
    user_email = (getattr(getattr(empregado, "user", None), "email", "") or "").strip()
    empregado_email = (getattr(empregado, "email", "") or "").strip()
    return user_email or empregado_email


def _emails_empresa(avaria):
    empresa = getattr(avaria, "empresa", None)
    if not empresa:
        return []
    emails = []
    for valor in [
        getattr(empresa, "email", ""),
        getattr(empresa, "responsavel_email", ""),
    ]:
        valor = (valor or "").strip()
        if valor:
            emails.append(valor)
    return emails


def _backend_entrega_real():
    backend = (getattr(settings, "EMAIL_BACKEND", "") or "").strip()
    return backend not in BACKENDS_SEM_ENTREGA_REAL


def _enviar(*, assunto, mensagem, destinos):
    destinos_unicos = []
    for email in destinos:
        email = (email or "").strip()
        if email and email not in destinos_unicos:
            destinos_unicos.append(email)
    if not destinos_unicos or not _backend_entrega_real():
        return 0
    return send_mail(
        subject=assunto,
        message=mensagem,
        from_email=_resolver_from_email(),
        recipient_list=destinos_unicos,
        fail_silently=False,
    )


def notificar_atribuicao_responsavel(*, avaria):
    if not avaria.responsavel_empregado_id:
        return 0

    furo_nome = getattr(getattr(avaria, "furo", None), "nome", "-")
    projeto_nome = getattr(getattr(avaria, "projeto", None), "nome", "-")
    reportado_por = getattr(getattr(avaria, "reportado_por", None), "nome", "-")
    responsavel_nome = getattr(getattr(avaria, "responsavel_empregado", None), "nome", "-")

    assunto = f"[Sistema Furação] Avaria atribuída: {avaria.maquina.nome}"
    mensagem = (
        "Foi-te atribuída uma avaria de máquina.\n\n"
        f"Máquina: {avaria.maquina.nome}\n"
        f"Estado atual: {avaria.get_status_display()}\n"
        f"Projeto: {projeto_nome}\n"
        f"Furo: {furo_nome}\n"
        f"Reportado por: {reportado_por}\n"
        f"Responsável: {responsavel_nome}\n"
        f"Data início: {avaria.data_inicio:%d/%m/%Y %H:%M}\n\n"
        f"Descrição:\n{avaria.descricao}\n"
    )

    destinos = _emails_empresa(avaria)
    destinos.append(_email_empregado(avaria.responsavel_empregado))
    return _enviar(assunto=assunto, mensagem=mensagem, destinos=destinos)


def notificar_mudanca_estado(*, avaria, ator_nome="Sistema"):
    furo_nome = getattr(getattr(avaria, "furo", None), "nome", "-")
    projeto_nome = getattr(getattr(avaria, "projeto", None), "nome", "-")
    reportado_por = getattr(getattr(avaria, "reportado_por", None), "nome", "-")
    responsavel_nome = getattr(getattr(avaria, "responsavel_empregado", None), "nome", "-")

    assunto = f"[Sistema Furação] Estado da avaria atualizado: {avaria.maquina.nome}"
    mensagem = (
        "O estado de uma avaria foi atualizado.\n\n"
        f"Máquina: {avaria.maquina.nome}\n"
        f"Novo estado: {avaria.get_status_display()}\n"
        f"Projeto: {projeto_nome}\n"
        f"Furo: {furo_nome}\n"
        f"Reportado por: {reportado_por}\n"
        f"Responsável: {responsavel_nome or '-'}\n"
        f"Atualizado por: {ator_nome}\n"
        f"Data início: {avaria.data_inicio:%d/%m/%Y %H:%M}\n"
        f"Data fim: {avaria.data_fim:%d/%m/%Y %H:%M}\n" if avaria.data_fim else "Data fim: -\n"
    )
    mensagem += f"\nDescrição:\n{avaria.descricao}\n"
    if avaria.solucao:
        mensagem += f"\nSolução:\n{avaria.solucao}\n"

    destinos = _emails_empresa(avaria)
    destinos.append(_email_empregado(avaria.reportado_por))
    destinos.append(_email_empregado(avaria.responsavel_empregado))
    return _enviar(assunto=assunto, mensagem=mensagem, destinos=destinos)
