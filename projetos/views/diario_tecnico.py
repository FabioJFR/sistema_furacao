import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from projetos.decorators import empregado_required
from projetos.services.acesso_contexto import obter_empregado_autenticado_contexto
from projetos.services.diario_tecnico import construir_contexto_diario_tecnico

logger = logging.getLogger("core")

# Multiempresa: o diário técnico deve ser mostrado apenas a empregados com empresa válida.

def _obter_empregado_autenticado_diario(request):
    logger.debug(
        "A resolver empregado autenticado em diario_tecnico.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado, _ligado_por_fallback, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
        vincular_por_email=True,
    )
    if resposta_erro:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em diario_tecnico.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro

    return empregado, None

@login_required
@empregado_required
def diario_tecnico(request):
    logger.info(
        "Entrada na view diario_tecnico. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_diario(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view diario_tecnico. user_id=%s", request.user.id)
        return resposta_erro

    context = construir_contexto_diario_tecnico(empregado=empregado)
    logger.info(
        "View diario_tecnico carregada com sucesso. user_id=%s, empregado_id=%s, total_secoes=%s, total_referencias=%s",
        request.user.id,
        empregado.id,
        len(context["secoes"]),
        len(context["referencias"]),
    )
    return render(request, "projetos/diario_tecnico.html", context)
