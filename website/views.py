from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth import logout

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
        resultado = services.executar_registo(request.POST)
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
            "Conta criada com sucesso. Já podes iniciar sessão.",
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
