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
from projetos.selectors.acesso import obter_perfil_ativo_por_user
from projetos.services.acesso_contexto import (
    obter_empresa_admin_contexto,
    obter_empregado_autenticado_contexto,
)
from projetos.services.despesas import apagar_despesa, criar_despesa

logger = logging.getLogger("core")


def _user_conta_individual(user):
    perfil = obter_perfil_ativo_por_user(user)
    return bool(perfil and perfil.tipo_acesso == "individual")


@login_required
@admin_required
def despesa_list_admin(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
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
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        return resposta_erro

    if request.method == "POST":
        form = DespesaForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            criar_despesa(form=form, empresa=empresa)
            messages.success(request, "Despesa adicionada com sucesso.")
            return redirect("projetos:despesa_list_admin")
        messages.error(request, "Erro ao adicionar despesa. Verifica os dados.")
    else:
        form = DespesaForm(empresa=empresa)

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
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        return resposta_erro

    despesa = obter_despesa_admin(empresa=empresa, despesa_id=despesa_id)
    return render(request, "projetos/despesa_detail.html", {"despesa": despesa})


@login_required
@admin_required
def despesa_update_admin(request, despesa_id):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        return resposta_erro

    despesa = obter_despesa_admin(empresa=empresa, despesa_id=despesa_id)
    if request.method == "POST":
        form = DespesaForm(request.POST, request.FILES, instance=despesa, empresa=empresa)
        if form.is_valid():
            despesa = form.save(commit=False)
            despesa.empresa = empresa
            despesa.save()
            messages.success(request, "Despesa atualizada com sucesso.")
            return redirect("projetos:despesa_list_admin")
        messages.error(request, "Erro ao atualizar despesa. Verifica os dados.")
    else:
        form = DespesaForm(instance=despesa, empresa=empresa)

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
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        return resposta_erro

    despesa = obter_despesa_admin(empresa=empresa, despesa_id=despesa_id)
    if request.method == "POST":
        apagar_despesa(despesa=despesa)
        messages.success(request, "Despesa apagada com sucesso.")
        return redirect("projetos:despesa_list_admin")

    return render(request, "projetos/despesa_confirm_delete.html", {"despesa": despesa})


@login_required
@empregado_required
def despesa_list_empregado(request):
    if not _user_conta_individual(request.user):
        messages.error(request, "A área de Despesas está disponível apenas para contas individuais.")
        return redirect("projetos:area_empregado")

    empregado, _, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
        vincular_por_email=True,
    )
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
    if not _user_conta_individual(request.user):
        messages.error(request, "A área de Despesas está disponível apenas para contas individuais.")
        return redirect("projetos:area_empregado")

    empregado, _, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
        vincular_por_email=True,
    )
    if resposta_erro:
        return resposta_erro

    if request.method == "POST":
        form = DespesaForm(
            request.POST,
            request.FILES,
            empresa=empregado.empresa,
            empregado=empregado,
        )
        if form.is_valid():
            criar_despesa(form=form, empresa=empregado.empresa)
            messages.success(request, "Despesa adicionada com sucesso.")
            return redirect("projetos:despesa_list_empregado")
        messages.error(request, "Erro ao adicionar despesa. Verifica os dados.")
    else:
        form = DespesaForm(empresa=empregado.empresa, empregado=empregado)

    return render(
        request,
        "projetos/despesa_form.html",
        {
            "form": form,
            "titulo": "Adicionar despesa",
            "voltar_url": "projetos:despesa_list_empregado",
        },
    )
