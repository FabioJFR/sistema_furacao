import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..decorators import admin_required
from ..forms.medicao import MedicaoForm
from projetos.selectors.furos import obter_furo
from projetos.selectors.medicoes import (
    obter_lista_medicoes,
    obter_medicao,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.medicoes import (
    apagar_medicao,
    processar_fluxo_form_medicao,
)

logger = logging.getLogger("core")


# ---------------- HELPERS ----------------
def _obter_empresa_admin_medicoes(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        logger.warning(
            "Falha ao resolver empresa administrativa em medicoes.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empresa, None


def _render_medicao_form(request, form, titulo, furo, medicao=None):
    context = {
        "form": form,
        "titulo": titulo,
        "furo": furo,
    }
    if medicao is not None:
        context["medicao"] = medicao
    return render(request, "projetos/medicao_form.html", context)


# Multiempresa: o administrador só pode listar e gerir medições da sua própria empresa.
@login_required
@admin_required
def medicao_list(request):
    logger.info(
        "Entrada na view medicao_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_medicoes(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view medicao_list. user_id=%s", request.user.id)
        return resposta_erro

    medicoes = obter_lista_medicoes(empresa=empresa)

    logger.info(
        "View medicao_list carregada com sucesso. user_id=%s, empresa_id=%s, total_medicoes=%s",
        request.user.id,
        empresa.id,
        medicoes.count() if hasattr(medicoes, "count") else "n/a",
    )
    return render(
        request,
        "projetos/medicao_list.html",
        {"medicoes": medicoes},
    )


@login_required
@admin_required
def medicao_create(request, furo_id):
    logger.info(
        "Entrada na view medicao_create. user_id=%s, username='%s', furo_id=%s, method=%s",
        request.user.id,
        request.user.username,
        furo_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_medicoes(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view medicao_create. user_id=%s", request.user.id)
        return resposta_erro

    furo = obter_furo(furo_id, empresa=empresa)

    fluxo = processar_fluxo_form_medicao(
        method=request.method,
        post_data=request.POST,
        files_data=request.FILES,
        form_class=MedicaoForm,
        empresa=empresa,
        furo=furo,
        sucesso_msg="Medição criada com sucesso.",
        erro_msg="Erro ao criar a medição. Verifique os dados.",
        acao="create",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["ok"]:
            logger.info(
                "Medição criada com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
                request.user.id,
                empresa.id,
                furo.pk,
            )
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect(furo)

        if resultado["erro"]:
            logger.warning(
                "Erro de validação ao criar medição. user_id=%s, furo_id=%s, erro=%s",
                request.user.id,
                furo_id,
                resultado["erro"],
            )
        else:
            logger.warning(
                "Erro ao criar medição. user_id=%s, furo_id=%s, erros=%s",
                request.user.id,
                furo_id,
                form.errors,
            )
        messages.error(request, resultado["mensagem_erro"])

    return _render_medicao_form(request, form, f"Nova Medição - {furo.nome}", furo=furo)

@login_required
@admin_required
def medicao_update(request, pk):
    logger.info(
        "Entrada na view medicao_update. user_id=%s, username='%s', medicao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_medicoes(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view medicao_update. user_id=%s", request.user.id)
        return resposta_erro

    medicao = obter_medicao(pk, empresa=empresa)

    fluxo = processar_fluxo_form_medicao(
        method=request.method,
        post_data=request.POST,
        files_data=request.FILES,
        form_class=MedicaoForm,
        empresa=empresa,
        furo=medicao.furo,
        instance=medicao,
        sucesso_msg="Medição atualizada com sucesso.",
        erro_msg="Erro ao atualizar a medição. Verifique os dados.",
        acao="update",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["ok"]:
            logger.info(
                "Medição atualizada com sucesso. user_id=%s, empresa_id=%s, medicao_id=%s",
                request.user.id,
                empresa.id,
                medicao.pk,
            )
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect("projetos:medicao_list")

        if resultado["erro"]:
            logger.warning(
                "Erro de validação ao atualizar medição. user_id=%s, medicao_pk=%s, erro=%s",
                request.user.id,
                pk,
                resultado["erro"],
            )
        else:
            logger.warning(
                "Erro ao atualizar medição. user_id=%s, medicao_pk=%s, erros=%s",
                request.user.id,
                pk,
                form.errors,
            )
        messages.error(request, resultado["mensagem_erro"])

    return _render_medicao_form(
        request,
        form,
        f"Editar Medição - {medicao.furo.nome}",
        furo=medicao.furo,
        medicao=medicao,
    )

@login_required
@admin_required
def medicao_delete(request, pk):
    logger.info(
        "Entrada na view medicao_delete. user_id=%s, username='%s', medicao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_medicoes(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view medicao_delete. user_id=%s", request.user.id)
        return resposta_erro

    medicao = obter_medicao(pk, empresa=empresa)

    if request.method == "POST":
        medicao_id = apagar_medicao(medicao=medicao, empresa=empresa)
        logger.info(
            "Medição apagada com sucesso. user_id=%s, empresa_id=%s, medicao_id=%s",
            request.user.id,
            empresa.id,
            medicao_id,
        )
        messages.success(request, "Medição apagada com sucesso.")
        return redirect("projetos:medicao_list")

    return render(
        request,
        "projetos/medicao_confirm_delete.html",
        {
            "medicao": medicao,
            "furo": medicao.furo,
        },
    )
