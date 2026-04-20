from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from django.contrib.auth import logout

from plataforma.models import Empresa, PerfilPlataforma, Plano


def home(request):
    planos = Plano.objects.filter(ativo=True).order_by("preco_mensal")
    return render(
        request,
        "website/home.html",
        {
            "planos": planos[:3],
        },
    )


def planos(request):
    planos_qs = Plano.objects.filter(ativo=True).order_by("preco_mensal")
    return render(
        request,
        "website/planos.html",
        {
            "planos": planos_qs,
        },
    )


@transaction.atomic
def registo(request):
    planos_qs = Plano.objects.filter(ativo=True).order_by("preco_mensal")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password1 = request.POST.get("password1") or ""
        password2 = request.POST.get("password2") or ""
        nome_empresa = (request.POST.get("nome_empresa") or "").strip()
        nome_responsavel = (request.POST.get("nome_responsavel") or "").strip()
        plano_id = request.POST.get("plano")
        tipo_conta = request.POST.get("tipo_conta") or "empresa"

        erros = []

        if not username:
            erros.append("O username é obrigatório.")

        if User.objects.filter(username=username).exists():
            erros.append("Já existe um utilizador com esse username.")

        if email and User.objects.filter(email=email).exists():
            erros.append("Já existe um utilizador com esse email.")

        if not password1 or not password2:
            erros.append("A password é obrigatória.")
        elif password1 != password2:
            erros.append("As passwords não coincidem.")

        plano = Plano.objects.filter(pk=plano_id, ativo=True).first()
        if not plano:
            erros.append("Seleciona um plano válido.")
        else:
            if plano.tipo == "empresa" and tipo_conta != "empresa":
                erros.append("O plano escolhido exige conta do tipo empresa.")

            if plano.tipo == "individual" and tipo_conta != "individual":
                erros.append("O plano escolhido exige conta do tipo individual.")

        if tipo_conta == "empresa" and not nome_empresa:
            erros.append("O nome da empresa é obrigatório para conta empresa.")

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(
                request,
                "website/registo.html",
                {
                    "planos": planos_qs,
                    "dados": request.POST,
                },
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            is_active=True,
        )

        empresa = None
        tipo_acesso = "individual"

        if tipo_conta == "empresa":
            empresa = Empresa.objects.create(
                nome=nome_empresa,
                nome_comercial=nome_empresa,
                email=email,
                responsavel_nome=nome_responsavel,
                responsavel_email=email,
                plano=plano,
                status="ativa",
                data_inicio=timezone.now().date(),
                ativo=True,
            )
            tipo_acesso = "empresa_admin"

        PerfilPlataforma.objects.create(
            user=user,
            tipo_acesso=tipo_acesso,
            empresa=empresa,
            ativo=True,
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
        },
    )


def logout_user(request):
    logout(request)
    return redirect("website:home")