import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..decorators import admin_required
from ..forms.maquina import MaquinaForm
from projetos.selectors.maquinas import (
    obter_contexto_maquina_detail,
    obter_lista_maquinas,
    obter_maquina,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.maquinas import (
    apagar_maquina,
    atualizar_maquina,
    criar_maquina,
)

logger = logging.getLogger("core")


# ---------------- HELPERS ----------------
def _obter_empresa_admin_maquinas(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        logger.warning(
            "Falha ao resolver empresa administrativa em maquinas.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empresa, None


def _render_maquina_form(request, form, titulo, maquina=None):
    context = {
        "form": form,
        "titulo": titulo,
    }
    if maquina is not None:
        context["maquina"] = maquina
    return render(request, "projetos/maquina_form.html", context)


def _processar_form_maquina(
    *,
    request,
    form,
    empresa,
    on_success,
    sucesso_msg,
    erro_msg,
    log_sucesso,
    log_erro,
):
    if not form.is_valid():
        logger.warning(log_erro, request.user.id, form.errors)
        messages.error(request, erro_msg)
        return None

    maquina = on_success(form, empresa=empresa)
    logger.info(log_sucesso, request.user.id, empresa.id, maquina.id)
    messages.success(request, sucesso_msg)
    return maquina


# Multiempresa: o administrador só pode listar e gerir máquinas da sua própria empresa.
@login_required
@admin_required
def maquina_list(request):
    logger.info(
        "Entrada na view maquina_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_maquinas(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view maquina_list. user_id=%s", request.user.id)
        return resposta_erro

    maquinas = obter_lista_maquinas(empresa=empresa)
    logger.info(
        "View maquina_list carregada com sucesso. user_id=%s, empresa_id=%s, total_maquinas=%s",
        request.user.id,
        empresa.id,
        maquinas.count() if hasattr(maquinas, "count") else "n/a",
    )
    return render(request, "projetos/maquina_list.html", {
        "maquinas": maquinas
    })


@login_required
@admin_required
def maquina_detail(request, maquina_id):
    logger.info(
        "Entrada na view maquina_detail. user_id=%s, username='%s', maquina_id=%s",
        request.user.id,
        request.user.username,
        maquina_id,
    )
    empresa, resposta_erro = _obter_empresa_admin_maquinas(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view maquina_detail. user_id=%s", request.user.id)
        return resposta_erro

    context = obter_contexto_maquina_detail(maquina_id, empresa=empresa)
    logger.info(
        "View maquina_detail carregada com sucesso. user_id=%s, empresa_id=%s, maquina_id=%s",
        request.user.id,
        empresa.id,
        maquina_id,
    )
    return render(request, "projetos/maquina_detail.html", context)


@login_required
@admin_required
def maquina_create(request):
    logger.info(
        "Entrada na view maquina_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_maquinas(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view maquina_create. user_id=%s", request.user.id)
        return resposta_erro

    if request.method == "POST":
        form = MaquinaForm(request.POST, empresa=empresa)
        maquina = _processar_form_maquina(
            request=request,
            form=form,
            empresa=empresa,
            on_success=criar_maquina,
            sucesso_msg="Máquina criada com sucesso.",
            erro_msg="Erro ao criar a máquina. Verifique os dados.",
            log_sucesso="Máquina criada com sucesso. user_id=%s, empresa_id=%s, maquina_id=%s",
            log_erro="Erro ao criar máquina. user_id=%s, erros=%s",
        )
        if maquina:
            return redirect("projetos:maquina_detail", maquina_id=maquina.id)
    else:
        form = MaquinaForm(empresa=empresa)

    return _render_maquina_form(request, form, "Nova Máquina")


@login_required
@admin_required
def maquina_update(request, maquina_id):
    logger.info(
        "Entrada na view maquina_update. user_id=%s, username='%s', maquina_id=%s, method=%s",
        request.user.id,
        request.user.username,
        maquina_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_maquinas(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view maquina_update. user_id=%s", request.user.id)
        return resposta_erro

    maquina = obter_maquina(maquina_id, empresa=empresa)

    if request.method == "POST":
        form = MaquinaForm(request.POST, instance=maquina, empresa=empresa)
        maquina_atualizada = _processar_form_maquina(
            request=request,
            form=form,
            empresa=empresa,
            on_success=atualizar_maquina,
            sucesso_msg="Máquina atualizada com sucesso.",
            erro_msg="Erro ao atualizar a máquina. Verifique os dados.",
            log_sucesso="Máquina atualizada com sucesso. user_id=%s, empresa_id=%s, maquina_id=%s",
            log_erro="Erro ao atualizar máquina. user_id=%s, erros=%s",
        )
        if maquina_atualizada:
            return redirect("projetos:maquina_detail", maquina_id=maquina_atualizada.id)
    else:
        form = MaquinaForm(instance=maquina, empresa=empresa)

    return _render_maquina_form(request, form, "Editar Máquina", maquina=maquina)


@login_required
@admin_required
def maquina_delete(request, maquina_id):
    logger.info(
        "Entrada na view maquina_delete. user_id=%s, username='%s', maquina_id=%s, method=%s",
        request.user.id,
        request.user.username,
        maquina_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_maquinas(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view maquina_delete. user_id=%s", request.user.id)
        return resposta_erro

    maquina = obter_maquina(maquina_id, empresa=empresa)

    if request.method == "POST":
        maquina_id_removida = apagar_maquina(maquina=maquina, empresa=empresa)
        logger.info(
            "Máquina apagada com sucesso. user_id=%s, empresa_id=%s, maquina_id=%s",
            request.user.id,
            empresa.id,
            maquina_id_removida,
        )
        messages.success(request, "Máquina apagada com sucesso.")
        return redirect("projetos:maquina_list")

    return render(request, 'projetos/maquina_confirm_delete.html', {
        'maquina': maquina
    })
