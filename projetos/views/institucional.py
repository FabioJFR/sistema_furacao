from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def ajuda(request):
    return render(
        request,
        "projetos/ajuda.html",
        {
            "titulo": "Ajuda",
        },
    )


@login_required
def sobre(request):
    return render(
        request,
        "projetos/sobre.html",
        {
            "titulo": "Sobre",
        },
    )


@login_required
def termos_condicoes(request):
    return render(
        request,
        "projetos/termos_condicoes.html",
        {
            "titulo": "Termos & Condições",
        },
    )


@login_required
def politica_privacidade(request):
    return render(
        request,
        "projetos/politica_privacidade.html",
        {
            "titulo": "Política de Privacidade",
        },
    )
