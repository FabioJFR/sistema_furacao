from django.conf import settings
from django.core.mail import send_mail

from projetos.selectors.sugestoes import listar_emails_superusers


BACKENDS_SEM_ENTREGA_REAL = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
}


def _listar_emails_destino_sugestoes():
    destinos_configurados = list(getattr(settings, "SUGESTOES_EMAIL_DESTINO", []) or [])
    destinos_limpos = [email.strip() for email in destinos_configurados if (email or "").strip()]
    if destinos_limpos:
        return destinos_limpos
    return listar_emails_superusers()


def enviar_sugestao_para_superusers(*, sugestao):
    emails_destino = _listar_emails_destino_sugestoes()
    if not emails_destino:
        return False, "", "Nenhum email de destino configurado para receber sugestões."

    backend = getattr(settings, "EMAIL_BACKEND", "")
    if backend in BACKENDS_SEM_ENTREGA_REAL:
        return (
            False,
            emails_destino[0],
            f"EMAIL_BACKEND atual ({backend}) não entrega emails reais.",
        )

    assunto = f"[Sistema Furação] Nova sugestão ({sugestao.get_avaliacao_display()})"
    mensagem = (
        "Nova sugestão recebida na plataforma.\n\n"
        f"Utilizador: {sugestao.user.username}\n"
        f"Email do utilizador: {sugestao.user.email or '-'}\n"
        f"Avaliação: {sugestao.get_avaliacao_display()}\n\n"
        f"Opinião:\n{sugestao.opiniao or '-'}\n\n"
        f"Sugestões:\n{sugestao.sugestoes}\n"
    )

    enviados = send_mail(
        subject=assunto,
        message=mensagem,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=emails_destino,
        fail_silently=False,
    )
    if enviados and enviados > 0:
        return True, emails_destino[0], ""

    return False, emails_destino[0], "O backend não confirmou envio de email."
