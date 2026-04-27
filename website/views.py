from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.utils.translation import gettext as _

from website import selectors
from website import services


def home(request):
    planos = selectors.listar_planos_ativos()
    return render(
        request,
        "website/home.html",
        {
            "planos": planos[:3],
        },
    )


def planos(request):
    planos_qs = selectors.listar_planos_ativos()
    return render(
        request,
        "website/planos.html",
        {
            "planos": planos_qs,
        },
    )


def registo(request):
    planos_qs = selectors.listar_planos_ativos()
    planos_contexto = selectors.construir_planos_contexto(planos_qs)

    if request.method == "POST":
        resultado = services.executar_registo(request.POST, request=request)
        if not resultado.sucesso:
            for erro in resultado.erros:
                messages.error(request, erro)
            return render(
                request,
                "website/registo.html",
                {
                    "planos": planos_qs,
                    "dados": request.POST,
                    "planos_contexto": planos_contexto,
                },
            )

        messages.success(
            request,
            _("Conta criada com sucesso. Enviámos um email para confirmares a conta antes do primeiro login."),
        )
        return redirect("login")

    return render(
        request,
        "website/registo.html",
        {
            "planos": planos_qs,
            "planos_contexto": planos_contexto,
        },
    )


def logout_user(request):
    logout(request)
    return redirect("website:home")


def confirmar_conta(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.filter(pk=uid).first()
    except (TypeError, ValueError, OverflowError):
        user = None

    if not user:
        messages.error(request, _("Link de confirmação inválido."))
        return redirect("login")

    if user.is_active:
        messages.info(request, _("A tua conta já está confirmada. Podes iniciar sessão."))
        return redirect("login")

    if not default_token_generator.check_token(user, token):
        messages.error(request, _("Este link de confirmação é inválido ou já expirou."))
        return redirect("login")

    user.is_active = True
    user.save(update_fields=["is_active"])
    messages.success(request, _("Conta confirmada com sucesso. Já podes iniciar sessão."))
    return redirect("login")


def reenviar_confirmacao(request):
    if request.method != "POST":
        return redirect("login")

    email = (request.POST.get("email") or "").strip()
    if not email:
        messages.error(request, _("Indica o email para reenviar a confirmação."))
        return redirect("login")

    try:
        services.reenviar_confirmacao_por_email(email=email, request=request)
    except Exception:
        messages.error(
            request,
            _("Não foi possível reenviar o email de confirmação neste momento. Tenta novamente."),
        )
        return redirect("login")

    messages.success(
        request,
        _("Se existir uma conta pendente com esse email, enviámos um novo link de confirmação."),
    )
    return redirect("login")
