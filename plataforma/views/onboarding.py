import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from plataforma.decorators import platform_admin_required
from plataforma.selectors.planos import (
    construir_planos_periodos_precos,
    listar_planos_ativos,
)
from plataforma.services.onboarding import (
    processar_fluxo_onboarding_empresa,
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

    fluxo = processar_fluxo_onboarding_empresa(
        method=request.method,
        post_data=request.POST,
        files_data=request.FILES,
        actor_user_id=getattr(request.user, "id", None),
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["ok"]:
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect("plataforma:onboarding_empresa")
        messages.error(request, resultado["mensagem_erro"])
    else:
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
