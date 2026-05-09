import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..decorators import admin_required
from ..forms.maquina import MaquinaForm, MaquinaTurnoForm
from projetos.selectors.maquinas import (
    obter_contexto_maquina_detail,
    obter_lista_maquinas,
    obter_maquina,
    obter_maquina_turno,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.maquinas import (
    apagar_maquina,
    apagar_maquina_turno,
    atualizar_maquina_turno,
    criar_maquina_turno,
    processar_fluxo_form_maquina,
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


def _render_maquina_turno_form(request, form, titulo, maquina, turno=None):
    context = {
        "form": form,
        "titulo": titulo,
        "maquina": maquina,
    }
    if turno is not None:
        context["turno_item"] = turno
    return render(request, "projetos/maquina_turno_form.html", context)


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

    fluxo = processar_fluxo_form_maquina(
        method=request.method,
        post_data=request.POST,
        form_class=MaquinaForm,
        empresa=empresa,
        acao="create",
        sucesso_msg="Máquina criada com sucesso.",
        erro_msg="Erro ao criar a máquina. Verifique os dados.",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["ok"]:
            maquina = resultado["maquina"]
            logger.info(
                "Máquina criada com sucesso. user_id=%s, empresa_id=%s, maquina_id=%s",
                request.user.id,
                empresa.id,
                maquina.id,
            )
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect("projetos:maquina_detail", maquina_id=maquina.id)
        logger.warning(
            "Erro ao criar máquina. user_id=%s, erros=%s",
            request.user.id,
            resultado.get("erros_form"),
        )
        messages.error(request, resultado["mensagem_erro"])

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

    fluxo = processar_fluxo_form_maquina(
        method=request.method,
        post_data=request.POST,
        form_class=MaquinaForm,
        empresa=empresa,
        acao="update",
        sucesso_msg="Máquina atualizada com sucesso.",
        erro_msg="Erro ao atualizar a máquina. Verifique os dados.",
        instance=maquina,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["ok"]:
            maquina_atualizada = resultado["maquina"]
            logger.info(
                "Máquina atualizada com sucesso. user_id=%s, empresa_id=%s, maquina_id=%s",
                request.user.id,
                empresa.id,
                maquina_atualizada.id,
            )
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect("projetos:maquina_detail", maquina_id=maquina_atualizada.id)
        logger.warning(
            "Erro ao atualizar máquina. user_id=%s, erros=%s",
            request.user.id,
            resultado.get("erros_form"),
        )
        messages.error(request, resultado["mensagem_erro"])

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


@login_required
@admin_required
def maquina_turno_create(request, maquina_id):
    empresa, resposta_erro = _obter_empresa_admin_maquinas(request)
    if resposta_erro:
        return resposta_erro

    maquina = obter_maquina(maquina_id, empresa=empresa)
    form = MaquinaTurnoForm(request.POST or None, empresa=empresa, maquina=maquina)
    if request.method == "POST" and form.is_valid():
        criar_maquina_turno(form=form, maquina=maquina, empresa=empresa)
        messages.success(request, "Turno da máquina criado com sucesso.")
        return redirect("projetos:maquina_detail", maquina_id=maquina.id)
    return _render_maquina_turno_form(request, form, "Novo Turno da Máquina", maquina=maquina)


@login_required
@admin_required
def maquina_turno_update(request, maquina_id, turno_id):
    empresa, resposta_erro = _obter_empresa_admin_maquinas(request)
    if resposta_erro:
        return resposta_erro

    maquina = obter_maquina(maquina_id, empresa=empresa)
    turno = obter_maquina_turno(turno_id, maquina=maquina, empresa=empresa)
    form = MaquinaTurnoForm(request.POST or None, instance=turno, empresa=empresa, maquina=maquina)
    if request.method == "POST" and form.is_valid():
        atualizar_maquina_turno(form=form, maquina=maquina, empresa=empresa)
        messages.success(request, "Turno da máquina atualizado com sucesso.")
        return redirect("projetos:maquina_detail", maquina_id=maquina.id)
    return _render_maquina_turno_form(request, form, "Editar Turno da Máquina", maquina=maquina, turno=turno)


@login_required
@admin_required
def maquina_turno_delete(request, maquina_id, turno_id):
    empresa, resposta_erro = _obter_empresa_admin_maquinas(request)
    if resposta_erro:
        return resposta_erro

    maquina = obter_maquina(maquina_id, empresa=empresa)
    turno = obter_maquina_turno(turno_id, maquina=maquina, empresa=empresa)

    if request.method == "POST":
        apagar_maquina_turno(turno=turno, maquina=maquina, empresa=empresa)
        messages.success(request, "Turno da máquina apagado com sucesso.")
        return redirect("projetos:maquina_detail", maquina_id=maquina.id)

    return render(
        request,
        "projetos/maquina_turno_confirm_delete.html",
        {
            "maquina": maquina,
            "turno_item": turno,
        },
    )
