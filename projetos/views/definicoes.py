import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import translation

from projetos.forms import PreferenciasForm
from projetos.selectors.acesso import resolver_empregado_por_user_ou_email
from projetos.selectors.preferencias import (
    garantir_preferencias_empresa,
    obter_ou_criar_preferencias_user,
)

logger = logging.getLogger("core")

# Multiempresa: as preferências devem estar sempre associadas à empresa do utilizador.

def _obter_empregado_autenticado_definicoes(request):
    logger.debug(
        "A resolver empregado autenticado em definicoes.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado, ligado_por_fallback = resolver_empregado_por_user_ou_email(request.user)
    if ligado_por_fallback and empregado is not None:
        logger.warning(
            "Ligação automática User -> Empregados executada em definicoes.py. user_id=%s, empregado_id=%s, empresa_id=%s, email='%s'",
            request.user.id,
            empregado.id,
            empregado.empresa_id,
            getattr(request.user, "email", ""),
        )
    if not empregado:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em definicoes.py. user_id=%s",
            request.user.id,
        )
        messages.error(
            request,
            "A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        )
        return None, redirect("projetos:redirect_after_login")

    if not empregado.empresa_id:
        logger.warning(
            "Empregado sem empresa associada em definicoes.py. user_id=%s, empregado_id=%s",
            request.user.id,
            empregado.id,
        )
        messages.error(request, "A tua conta não está associada a uma empresa. Contacta o administrador.")
        return None, redirect("projetos:redirect_after_login")

    return empregado, None

@login_required
def definicoes(request):
    logger.info(
        "Entrada na view definicoes. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_definicoes(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view definicoes. user_id=%s", request.user.id)
        return resposta_erro

    preferencias, _ = obter_ou_criar_preferencias_user(request.user)
    if empregado and empregado.empresa_id:
        preferencias = garantir_preferencias_empresa(preferencias, empregado.empresa)

    if request.method == "POST":
        form = PreferenciasForm(request.POST, instance=preferencias)

        if form.is_valid():
            preferencias = form.save(commit=False)

            if empregado and empregado.empresa_id:
                preferencias.empresa = empregado.empresa

            preferencias.save()

            # Ativar idioma imediatamente
            if preferencias.idioma:
                translation.activate(preferencias.idioma)
                request.session["django_language"] = preferencias.idioma

            logger.info(
                "Definições atualizadas com sucesso. user_id=%s, empregado_id=%s",
                request.user.id,
                empregado.id,
            )
            messages.success(request, "Definições guardadas com sucesso.")
            return redirect("projetos:definicoes")

        logger.warning(
            "Erro ao guardar definições. user_id=%s, empregado_id=%s, erros=%s",
            request.user.id,
            empregado.id,
            form.errors,
        )
        messages.error(request, "Erro ao guardar definições.")
    else:
        form = PreferenciasForm(instance=preferencias)

    return render(request, "projetos/definicoes.html", {
        "form": form,
        "titulo": "Definições",
    })
