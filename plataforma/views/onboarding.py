import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from plataforma.decorators import platform_admin_required
from plataforma.selectors.planos import construir_planos_periodos_precos, listar_planos_ativos
from plataforma.services.onboarding import (
    construir_form_onboarding_empresa,
    processar_submissao_onboarding_empresa,
)


logger = logging.getLogger("core")


# TODO futuro:
# - adicionar auditoria detalhada do onboarding
# - permitir convite por email em vez de password manual
# - reservar partes sensíveis do onboarding apenas ao platform_owner, se necessário


@platform_admin_required
@login_required
def onboarding_empresa(request):
    logger.info(
        "Entrada em onboarding_empresa. user_id=%s, method=%s",
        getattr(request.user, "id", None),
        request.method,
    )

    if request.method == "POST":
        logger.info(
            "POST recebido em onboarding_empresa. nome_empresa=%r, email_admin=%r, tipo_acesso=%r, criar_subscricao_inicial=%r",
            request.POST.get("nome_empresa"),
            request.POST.get("email_admin"),
            request.POST.get("tipo_acesso"),
            request.POST.get("criar_subscricao_inicial"),
        )
        resultado = processar_submissao_onboarding_empresa(
            post_data=request.POST,
            actor_user_id=getattr(request.user, "id", None),
        )
        form = resultado["form"]

        if resultado["ok"]:
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect("plataforma:onboarding_empresa")

        messages.error(request, resultado["mensagem_erro"])
    else:
        form = construir_form_onboarding_empresa()
        logger.debug(
            "Formulário onboarding_empresa aberto em GET. user_id=%s",
            getattr(request.user, "id", None),
        )

    planos = listar_planos_ativos()
    planos_periodos, planos_precos = construir_planos_periodos_precos(planos)

    return render(request, "plataforma/onboarding_empresa.html", {
        "form": form,
        "titulo": "Onboarding de Empresa",
        "planos_periodos": planos_periodos,
        "planos_precos": planos_precos,
    })
