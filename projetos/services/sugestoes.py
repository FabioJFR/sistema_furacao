from django.conf import settings
from django.core.mail import send_mail

from projetos.selectors.sugestoes import listar_emails_superusers


def enviar_sugestao_para_superusers(*, sugestao):
    emails_destino = listar_emails_superusers()
    if not emails_destino:
        return False, ""

    assunto = f"[Sistema Furação] Nova sugestão ({sugestao.get_avaliacao_display()})"
    mensagem = (
        "Nova sugestão recebida na plataforma.\n\n"
        f"Utilizador: {sugestao.user.username}\n"
        f"Email do utilizador: {sugestao.user.email or '-'}\n"
        f"Avaliação: {sugestao.get_avaliacao_display()}\n\n"
        f"Opinião:\n{sugestao.opiniao or '-'}\n\n"
        f"Sugestões:\n{sugestao.sugestoes}\n"
    )

    send_mail(
        subject=assunto,
        message=mensagem,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=emails_destino,
        fail_silently=False,
    )
    return True, emails_destino[0]

