import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.permissions import admin_required, empregado_required
from projetos.forms import DespesaForm
from projetos.selectors.despesas import (
    obter_despesa_admin,
    obter_lista_despesas_admin,
    obter_lista_despesas_empregado,
)
from projetos.services.acesso_contexto import (
    obter_empresa_admin_contexto,
)
from projetos.services.despesas import (
    processar_acao_apagar_despesa,
    processar_fluxo_form_despesa,
    resolver_empregado_individual_para_despesas,
)

logger = logging.getLogger("core")


def _obter_empresa_admin_despesas(request):
    return obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )


def _obter_empregado_individual_despesas(request):
    resultado = resolver_empregado_individual_para_despesas(request=request)
    if resultado.get("mensagem_erro"):
        messages.error(request, resultado["mensagem_erro"])
    if not resultado["ok"]:
        return None, resultado["resposta_erro"]
    return resultado["empregado"], None


@login_required
@admin_required
def despesa_list_admin(request):
    empresa, resposta_erro = _obter_empresa_admin_despesas(request)
    if resposta_erro:
        return resposta_erro

    despesas = obter_lista_despesas_admin(empresa=empresa)
    return render(
        request,
        "projetos/despesa_list.html",
        {
            "despesas": despesas,
            "titulo": "Minhas despesas",
            "adicionar_url": "projetos:despesa_create_admin",
        },
    )


@login_required
@admin_required
def despesa_create_admin(request):
    empresa, resposta_erro = _obter_empresa_admin_despesas(request)
    if resposta_erro:
        return resposta_erro

    fluxo = processar_fluxo_form_despesa(
        method=request.method,
        post_data=request.POST,
        files_data=request.FILES,
        form_class=DespesaForm,
        empresa=empresa,
        sucesso_msg="Despesa adicionada com sucesso.",
        erro_msg="Erro ao adicionar despesa. Verifica os dados.",
        acao="create",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect("projetos:despesa_list_admin")
        messages.error(request, resultado["mensagem_erro"])

    return render(
        request,
        "projetos/despesa_form.html",
        {
            "form": form,
            "titulo": "Adicionar despesa",
            "voltar_url": "projetos:despesa_list_admin",
        },
    )


@login_required
@admin_required
def despesa_detail_admin(request, despesa_id):
    empresa, resposta_erro = _obter_empresa_admin_despesas(request)
    if resposta_erro:
        return resposta_erro

    despesa = obter_despesa_admin(empresa=empresa, despesa_id=despesa_id)
    return render(request, "projetos/despesa_detail.html", {"despesa": despesa})


@login_required
@admin_required
def despesa_update_admin(request, despesa_id):
    empresa, resposta_erro = _obter_empresa_admin_despesas(request)
    if resposta_erro:
        return resposta_erro

    despesa = obter_despesa_admin(empresa=empresa, despesa_id=despesa_id)
    fluxo = processar_fluxo_form_despesa(
        method=request.method,
        post_data=request.POST,
        files_data=request.FILES,
        form_class=DespesaForm,
        empresa=empresa,
        sucesso_msg="Despesa atualizada com sucesso.",
        erro_msg="Erro ao atualizar despesa. Verifica os dados.",
        instance=despesa,
        acao="update",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect("projetos:despesa_list_admin")
        messages.error(request, resultado["mensagem_erro"])

    return render(
        request,
        "projetos/despesa_form.html",
        {
            "form": form,
            "titulo": "Editar despesa",
            "voltar_url": "projetos:despesa_list_admin",
        },
    )


@login_required
@admin_required
def despesa_delete_admin(request, despesa_id):
    empresa, resposta_erro = _obter_empresa_admin_despesas(request)
    if resposta_erro:
        return resposta_erro

    despesa = obter_despesa_admin(empresa=empresa, despesa_id=despesa_id)
    if request.method == "POST":
        resultado = processar_acao_apagar_despesa(despesa=despesa)
        messages.success(request, resultado["mensagem_sucesso"])
        return redirect("projetos:despesa_list_admin")

    return render(request, "projetos/despesa_confirm_delete.html", {"despesa": despesa})


@login_required
@empregado_required
def despesa_list_empregado(request):
    empregado, resposta_erro = _obter_empregado_individual_despesas(request)
    if resposta_erro:
        return resposta_erro

    despesas = obter_lista_despesas_empregado(empregado=empregado)
    return render(
        request,
        "projetos/despesa_list.html",
        {
            "despesas": despesas,
            "titulo": "Minhas despesas",
            "adicionar_url": "projetos:despesa_create_empregado",
        },
    )


@login_required
@empregado_required
def despesa_create_empregado(request):
    empregado, resposta_erro = _obter_empregado_individual_despesas(request)
    if resposta_erro:
        return resposta_erro

    fluxo = processar_fluxo_form_despesa(
        method=request.method,
        post_data=request.POST,
        files_data=request.FILES,
        form_class=DespesaForm,
        empresa=empregado.empresa,
        empregado=empregado,
        sucesso_msg="Despesa adicionada com sucesso.",
        erro_msg="Erro ao adicionar despesa. Verifica os dados.",
        acao="create",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect("projetos:despesa_list_empregado")
        messages.error(request, resultado["mensagem_erro"])

    return render(
        request,
        "projetos/despesa_form.html",
        {
            "form": form,
            "titulo": "Adicionar despesa",
            "voltar_url": "projetos:despesa_list_empregado",
        },
    )
