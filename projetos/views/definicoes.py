import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import translation

from projetos.forms import PreferenciasForm
from projetos.services.acesso_contexto import obter_empregado_autenticado_contexto
from projetos.services.definicoes import processar_fluxo_preferencias_utilizador_form
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

    empregado, ligado_por_fallback, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
        vincular_por_email=True,
    )
    if ligado_por_fallback and empregado is not None:
        logger.warning(
            "Ligação automática User -> Empregados executada em definicoes.py. user_id=%s, empregado_id=%s, empresa_id=%s, email='%s'",
            request.user.id,
            empregado.id,
            empregado.empresa_id,
            getattr(request.user, "email", ""),
        )
    if resposta_erro:
        logger.warning(
            "Utilizador sem contexto de empregado em definicoes.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro

    return empregado, None


def _aplicar_idioma_preferencias(request, preferencias):
    if preferencias.idioma:
        translation.activate(preferencias.idioma)
        request.session["django_language"] = preferencias.idioma


def _processar_form_definicoes(request, resultado, empregado):
    if not resultado["ok"]:
        logger.warning(
            "Erro ao guardar definições. user_id=%s, empregado_id=%s, erros=%s",
            request.user.id,
            getattr(empregado, "id", None),
            resultado.get("erros_form"),
        )
        messages.error(request, "Erro ao guardar definições.")
        return None

    preferencias = resultado["preferencias"]
    _aplicar_idioma_preferencias(request, preferencias)
    logger.info(
        "Definições atualizadas com sucesso. user_id=%s, empregado_id=%s",
        request.user.id,
        getattr(empregado, "id", None),
    )
    messages.success(request, "Definições guardadas com sucesso.")
    return redirect("projetos:definicoes")

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

    fluxo = processar_fluxo_preferencias_utilizador_form(
        method=request.method,
        post_data=request.POST,
        form_class=PreferenciasForm,
        preferencias=preferencias,
        user=request.user,
        empresa=empregado.empresa if empregado and empregado.empresa_id else None,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta = _processar_form_definicoes(request, resultado, empregado)
        if resposta:
            return resposta

    return render(request, "projetos/definicoes.html", {
        "form": form,
        "titulo": "Definições",
    })
