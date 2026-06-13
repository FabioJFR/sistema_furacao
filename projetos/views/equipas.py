import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from projetos.decorators import admin_required
from projetos.forms import EquipaForm
from projetos.models import Equipa
from projetos.services.acesso_contexto import obter_empresa_admin_contexto

logger = logging.getLogger("core")


def _obter_empresa_admin_equipas(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        logger.warning(
            "Falha ao resolver empresa administrativa em equipas.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empresa, None


def _obter_equipa_empresa(pk, empresa):
    return get_object_or_404(
        Equipa.objects.prefetch_related("membros"),
        pk=pk,
        empresa=empresa,
    )


@login_required
@admin_required
def equipa_list(request):
    empresa, resposta_erro = _obter_empresa_admin_equipas(request)
    if resposta_erro:
        return resposta_erro

    equipas = (
        Equipa.objects.filter(empresa=empresa)
        .prefetch_related("membros")
        .order_by("nome")
    )
    return render(request, "projetos/equipa_list.html", {"equipas": equipas})


@login_required
@admin_required
def equipa_create(request):
    empresa, resposta_erro = _obter_empresa_admin_equipas(request)
    if resposta_erro:
        return resposta_erro

    form = EquipaForm(request.POST or None, empresa=empresa)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Equipa criada com sucesso.")
            return redirect("projetos:equipa_list")
        messages.error(request, "Erro ao criar a equipa. Verifique os dados.")

    return render(
        request,
        "projetos/equipa_form.html",
        {"form": form, "titulo": "Nova Equipa", "is_create": True},
    )


@login_required
@admin_required
def equipa_update(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_equipas(request)
    if resposta_erro:
        return resposta_erro

    equipa = _obter_equipa_empresa(pk, empresa)
    form = EquipaForm(request.POST or None, instance=equipa, empresa=empresa)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Equipa atualizada com sucesso.")
            return redirect("projetos:equipa_list")
        messages.error(request, "Erro ao atualizar a equipa. Verifique os dados.")

    return render(
        request,
        "projetos/equipa_form.html",
        {"form": form, "titulo": "Editar Equipa", "equipa": equipa, "is_create": False},
    )


@login_required
@admin_required
def equipa_delete(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_equipas(request)
    if resposta_erro:
        return resposta_erro

    equipa = _obter_equipa_empresa(pk, empresa)
    if request.method == "POST":
        equipa.delete()
        messages.success(request, "Equipa apagada com sucesso.")
        return redirect("projetos:equipa_list")

    return render(request, "projetos/equipa_confirm_delete.html", {"equipa": equipa})
