#!/usr/bin/env python3
"""
Teste rápido de envio de email com as configurações do Django (.env).

Uso:
  python deploy/test_email.py
  python deploy/test_email.py --to sistemafuracao@gmail.com
"""

import argparse
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Testar envio SMTP com Django settings.")
    parser.add_argument("--to", dest="to_email", default="", help="Email de destino do teste.")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

    try:
        import django
        from django.conf import settings
        from django.core.mail import send_mail
    except Exception as exc:
        print(f"[ERRO] Não foi possível importar Django: {exc}")
        return 1

    django.setup()

    destino = (
        args.to_email.strip()
        or (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
        or (
            (getattr(settings, "SUGESTOES_EMAIL_DESTINO", []) or [""])[0].strip()
            if getattr(settings, "SUGESTOES_EMAIL_DESTINO", [])
            else ""
        )
    )

    if not destino:
        print("[ERRO] Sem destino de teste. Usa --to ou configura EMAIL_HOST_USER/SUGESTOES_EMAIL_DESTINO.")
        return 2

    assunto = "Teste SMTP - Sistema Furação"
    mensagem = (
        "Este é um teste de envio SMTP.\n\n"
        "Se recebeste esta mensagem, o email da plataforma está configurado corretamente."
    )

    print("=== Configuração ativa ===")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', '')}")
    print(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', '')}")
    print(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', '')}")
    print(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', '')}")
    print(f"DESTINO_TESTE: {destino}")
    print("==========================")

    try:
        enviados = send_mail(
            subject=assunto,
            message=mensagem,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", ""),
            recipient_list=[destino],
            fail_silently=False,
        )
        print(f"[OK] ENVIADOS={enviados}")
        return 0 if enviados and enviados > 0 else 3
    except Exception as exc:
        print(f"[ERRO] Falha no envio SMTP: {exc.__class__.__name__}: {exc}")
        return 4


if __name__ == "__main__":
    sys.exit(main())
