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
    destinos_superuser = listar_emails_superusers()
    if destinos_superuser:
        return destinos_superuser
    fallback = (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
    if fallback:
        return [fallback]
    return []


def _resolver_from_email():
    backend = (getattr(settings, "EMAIL_BACKEND", "") or "").strip()
    email_host_user = (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
    default_from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
    if backend == "django.core.mail.backends.smtp.EmailBackend" and email_host_user:
        return email_host_user
    return default_from_email or email_host_user or "noreply@sistemafuracao.local"


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
        from_email=_resolver_from_email(),
        recipient_list=emails_destino,
        fail_silently=False,
    )
    if enviados and enviados > 0:
        return True, emails_destino[0], ""

    return False, emails_destino[0], "O backend não confirmou envio de email."


def guardar_e_notificar_sugestao(*, form, user, logger):
    form.instance.user = user
    if not form.is_valid():
        return {"estado": "invalid"}

    try:
        sugestao = form.save(commit=False)
        try:
            enviado, email_destino, diagnostico_envio = enviar_sugestao_para_superusers(sugestao=sugestao)
        except Exception as exc:
            logger.exception(
                "Falha ao enviar sugestão por email. user_id=%s",
                user.id,
            )
            enviado = False
            email_destino = ""
            diagnostico_envio = f"Falha técnica no envio de email ({exc.__class__.__name__})."

        sugestao.enviado_por_email = enviado
        sugestao.email_destino = email_destino
        sugestao.save()

        if diagnostico_envio:
            logger.warning(
                "Sugestão sem entrega por email. user_id=%s, destino=%s, diagnostico=%s",
                user.id,
                email_destino or "-",
                diagnostico_envio,
            )

        return {
            "estado": "ok",
            "enviado": enviado,
            "diagnostico_envio": diagnostico_envio,
        }
    except Exception:
        logger.exception(
            "Erro ao processar sugestão na plataforma. user_id=%s",
            user.id,
        )
        return {"estado": "erro"}
