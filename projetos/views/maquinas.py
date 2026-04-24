import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..decorators import admin_required
from ..forms.maquina import MaquinaForm
from projetos.selectors.acesso import obter_contexto_admin_projetos
from projetos.selectors.maquinas import (
    obter_contexto_maquina_detail,
    obter_lista_maquinas,
    obter_maquina,
)
from projetos.services.maquinas import (
    atualizar_maquina,
    criar_maquina,
)

logger = logging.getLogger("core")


# ---------------- HELPERS ----------------
def _obter_contexto_admin_maquinas(request):
    logger.debug(
        "A resolver contexto administrativo em maquinas.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    perfil = obter_contexto_admin_projetos(request.user)
    if perfil:
        logger.info(
            "Contexto administrativo resolvido via PerfilPlataforma em maquinas.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em maquinas.py. user_id=%s",
        request.user.id,
    )
    return None



def _obter_empresa_admin_maquinas(request):
    contexto_admin = _obter_contexto_admin_maquinas(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or not empresa:
        logger.warning(
            "Contexto administrativo sem empresa em maquinas.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, None


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
        if form.is_valid():
            maquina = criar_maquina(form, empresa=empresa)
            logger.info(
                "Máquina criada com sucesso. user_id=%s, empresa_id=%s, maquina_id=%s",
                request.user.id,
                empresa.id,
                maquina.id,
            )
            messages.success(request, "Máquina criada com sucesso.")
            return redirect("projetos:maquina_detail", maquina_id=maquina.id)
        else:
            logger.warning(
                "Erro ao criar máquina. user_id=%s, erros=%s",
                request.user.id,
                form.errors,
            )
            messages.error(request, "Erro ao criar a máquina. Verifique os dados.")
    else:
        form = MaquinaForm(empresa=empresa)

    return render(request, 'projetos/maquina_form.html', {
        'form': form,
        'titulo': 'Nova Máquina'
    })


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
        if form.is_valid():
            maquina = atualizar_maquina(form, empresa=empresa)
            logger.info(
                "Máquina atualizada com sucesso. user_id=%s, empresa_id=%s, maquina_id=%s",
                request.user.id,
                empresa.id,
                maquina.id,
            )
            messages.success(request, "Máquina atualizada com sucesso.")
            return redirect("projetos:maquina_detail", maquina_id=maquina.id)
        else:
            logger.warning(
                "Erro ao atualizar máquina. user_id=%s, maquina_id=%s, erros=%s",
                request.user.id,
                maquina_id,
                form.errors,
            )
            messages.error(request, "Erro ao atualizar a máquina. Verifique os dados.")
    else:
        form = MaquinaForm(instance=maquina, empresa=empresa)

    return render(request, 'projetos/maquina_form.html', {
        'form': form,
        'titulo': 'Editar Máquina',
        'maquina': maquina
    })


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
        maquina_id_removida = maquina.id
        maquina.delete()
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
