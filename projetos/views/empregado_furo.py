import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.permissions import admin_required
from projetos.forms.empregado_furo import EmpregadoFuroForm
from projetos.selectors.empregados import (
    obter_furo_admin_por_pk_empresa,
    obter_ligacao_empregado_furo_admin_por_pk,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.empregado_furo import (
    criar_ligacao_empregado_furo,
    atualizar_ligacao_empregado_furo,
)
from projetos.services.empregados import garantir_ligacao_projeto_por_furo

logger = logging.getLogger("core")


# ---------------- HELPERS ----------------
def _obter_empresa_admin_empregado_furo(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        logger.warning(
            "Falha ao resolver empresa administrativa em empregado_furo.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empresa, None


def _render_form_empregado_furo(request, form, furo, titulo, ligacao=None):
    context = {
        "form": form,
        "furo": furo,
        "titulo": titulo,
    }
    if ligacao is not None:
        context["ligacao"] = ligacao
    return render(request, "projetos/furo_adicionar_empregado.html", context)


def _preparar_form_empregado_furo(*, request, empresa, furo, instance=None):
    form = EmpregadoFuroForm(
        request.POST if request.method == "POST" else None,
        instance=instance,
        empresa=empresa,
        furo=furo,
    )
    form.instance.furo = furo
    form.instance.empresa = empresa
    empregado_id = request.POST.get("empregado")
    if empregado_id:
        form.instance.empregado_id = empregado_id
    return form


# Multiempresa: a gestão de trabalhadores por furo deve acontecer sempre dentro da empresa do administrador.
@login_required
@admin_required
def furo_adicionar_empregado(request, furo_id):
    logger.info(
        "Entrada na view furo_adicionar_empregado. user_id=%s, username='%s', furo_id=%s, method=%s",
        request.user.id,
        request.user.username,
        furo_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregado_furo(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_adicionar_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furo = obter_furo_admin_por_pk_empresa(furo_id, empresa)
    if furo.estado == "concluido":
        messages.error(request, "Este furo está terminado e já não aceita novos trabalhadores.")
        return redirect(furo)

    if request.method == "POST":
        form = _preparar_form_empregado_furo(
            request=request,
            empresa=empresa,
            furo=furo,
        )
        if form.is_valid():
            empregado = form.cleaned_data["empregado"]
            ligacao = criar_ligacao_empregado_furo(
                empregado=empregado,
                furo=furo,
                empresa=empresa,
                funcao=form.cleaned_data["funcao"],
                data_inicio=form.cleaned_data.get("data_inicio"),
                data_fim=form.cleaned_data.get("data_fim"),
                ativo=form.cleaned_data.get("ativo", True),
                observacoes=form.cleaned_data.get("observacoes"),
            )
            ligacao_projeto, projeto_criado = garantir_ligacao_projeto_por_furo(
                empregado=empregado,
                furo=furo,
                empresa=empresa,
                data_inicio=form.cleaned_data.get("data_inicio"),
            )

            logger.info(
                "Trabalhador associado ao furo com sucesso. user_id=%s, empresa_id=%s, furo_id=%s, ligacao_id=%s, ligacao_projeto_id=%s, ligacao_projeto_criada=%s",
                request.user.id,
                empresa.id,
                furo.id,
                ligacao.id,
                ligacao_projeto.id,
                projeto_criado,
            )
            if projeto_criado:
                messages.success(request, "Trabalhador associado ao furo e automaticamente ligado ao projeto.")
            else:
                messages.success(request, "Trabalhador associado ao furo com sucesso.")
            return redirect(furo)

        logger.warning(
            "Erro ao associar trabalhador ao furo. user_id=%s, furo_id=%s, erros=%s",
            request.user.id,
            furo_id,
            form.errors,
        )
        messages.error(request, "Erro ao associar trabalhador ao furo. Verifique os dados.")
    else:
        form = EmpregadoFuroForm(empresa=empresa, furo=furo)

    return _render_form_empregado_furo(
        request,
        form,
        furo,
        f"Adicionar Trabalhador ao Furo {furo.nome}",
    )


@login_required
@admin_required
def furo_editar_empregado(request, pk):
    logger.info(
        "Entrada na view furo_editar_empregado. user_id=%s, username='%s', ligacao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregado_furo(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_editar_empregado. user_id=%s", request.user.id)
        return resposta_erro

    ligacao = obter_ligacao_empregado_furo_admin_por_pk(pk, empresa)

    if request.method == "POST":
        form = _preparar_form_empregado_furo(
            request=request,
            empresa=empresa,
            furo=ligacao.furo,
            instance=ligacao,
        )
        if form.is_valid():
            empregado = form.cleaned_data["empregado"]
            ligacao = atualizar_ligacao_empregado_furo(
                ligacao=ligacao,
                empregado=empregado,
                empresa=empresa,
                funcao=form.cleaned_data["funcao"],
                data_inicio=form.cleaned_data.get("data_inicio"),
                data_fim=form.cleaned_data.get("data_fim"),
                ativo=form.cleaned_data.get("ativo", ligacao.ativo),
                observacoes=form.cleaned_data.get("observacoes"),
            )
            ligacao_projeto, projeto_criado = garantir_ligacao_projeto_por_furo(
                empregado=empregado,
                furo=ligacao.furo,
                empresa=empresa,
                data_inicio=form.cleaned_data.get("data_inicio"),
            )
            logger.info(
                "Ligação trabalhador/furo atualizada com sucesso. user_id=%s, empresa_id=%s, ligacao_id=%s, furo_id=%s, ligacao_projeto_id=%s, ligacao_projeto_criada=%s",
                request.user.id,
                empresa.id,
                ligacao.id,
                ligacao.furo.pk,
                ligacao_projeto.id,
                projeto_criado,
            )
            if projeto_criado:
                messages.success(request, "Ligação trabalhador/furo atualizada e projeto associado automaticamente.")
            else:
                messages.success(request, "Ligação trabalhador/furo atualizada com sucesso.")
            return redirect(ligacao.furo)

        logger.warning(
            "Erro ao atualizar ligação trabalhador/furo. user_id=%s, ligacao_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar ligação trabalhador/furo. Verifique os dados.")
    else:
        form = EmpregadoFuroForm(
            instance=ligacao,
            empresa=empresa,
            furo=ligacao.furo,
        )

    return _render_form_empregado_furo(
        request,
        form,
        ligacao.furo,
        f"Editar Trabalhador no Furo {ligacao.furo.nome}",
        ligacao=ligacao,
    )


@login_required
@admin_required
def furo_remover_empregado(request, pk):
    logger.info(
        "Entrada na view furo_remover_empregado. user_id=%s, username='%s', ligacao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregado_furo(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_remover_empregado. user_id=%s", request.user.id)
        return resposta_erro

    ligacao = obter_ligacao_empregado_furo_admin_por_pk(pk, empresa)
    furo = ligacao.furo

    if request.method == "POST":
        ligacao_id = ligacao.id
        ligacao.delete()
        logger.info(
            "Trabalhador removido do furo com sucesso. user_id=%s, empresa_id=%s, ligacao_id=%s, furo_id=%s",
            request.user.id,
            empresa.id,
            ligacao_id,
            furo.pk,
        )
        messages.success(request, "Trabalhador removido do furo com sucesso.")
        return redirect(furo)

    return render(request, "projetos/furo_remover_empregado.html", {
        "ligacao": ligacao,
        "furo": furo,
    })
