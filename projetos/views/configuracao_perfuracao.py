from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from core.permissions import admin_required
from projetos.decorators import empregado_required
from projetos.forms.configuracao_perfuracao import ConfiguracaoPerfuracaoEmpregadoForm
from projetos.models import ConfiguracaoPerfuracaoEmpregado, Empregados
from projetos.models import HistoricoConfiguracaoPerfuracao

from projetos.selectors.historico_configuracao import (
    obter_historico_configuracao_por_configuracao,
    obter_ultimo_historico_da_configuracao,
)

# ============================================================
# EMPREGADO
# ============================================================

@login_required
@empregado_required
def configuracao_perfuracao_list_empregado(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    configuracoes = (
        ConfiguracaoPerfuracaoEmpregado.objects
        .filter(empregado=empregado)
        .select_related("furo", "atualizado_por")
        .order_by("furo__nome")
    )

    return render(request, "projetos/configuracao_perfuracao_list_empregado.html", {
        "empregado": empregado,
        "configuracoes": configuracoes,
    })


@login_required
@empregado_required
def configuracao_perfuracao_create_empregado(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(request.POST, empregado=empregado)
        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.atualizado_por = request.user
            configuracao.save()
            HistoricoConfiguracaoPerfuracao.registar_historico(
                configuracao=configuracao,
                acao="criado",
                utilizador=request.user,
                observacoes="Configuração criada."
            )

            messages.success(request, "Configuração de perfuração criada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_empregado")
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(empregado=empregado)

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "titulo": "Nova Configuração de Perfuração",
        "modo_admin": False,
        "empregado_obj": empregado,
    })


@login_required
@empregado_required
def configuracao_perfuracao_update_empregado(request, pk):
    empregado = get_object_or_404(Empregados, user=request.user)

    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado,
        pk=pk,
        empregado=empregado
    )

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            request.POST,
            instance=configuracao,
            empregado=empregado
        )
        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.atualizado_por = request.user
            configuracao.save()
            HistoricoConfiguracaoPerfuracao.registar_historico(
                configuracao=configuracao,
                acao="editado",
                utilizador=request.user,
                observacoes="Configuração editada."
            )

            messages.success(request, "Configuração de perfuração atualizada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_empregado")
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            instance=configuracao,
            empregado=empregado
        )

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "titulo": "Editar Configuração de Perfuração",
        "modo_admin": False,
        "empregado_obj": empregado,
        "configuracao": configuracao,
    })


@login_required
@empregado_required
def configuracao_perfuracao_delete_empregado(request, pk):
    empregado = get_object_or_404(Empregados, user=request.user)

    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado,
        pk=pk,
        empregado=empregado
    )

    if request.method == "POST":
        HistoricoConfiguracaoPerfuracao.registar_historico(
            configuracao=configuracao,
            acao="apagado",
            utilizador=request.user,
            observacoes="Configuração apagada."
        )
        configuracao.delete()
        messages.success(request, "Configuração de perfuração apagada com sucesso.")
        return redirect("projetos:configuracao_perfuracao_list_empregado")

    return render(request, "projetos/configuracao_perfuracao_confirm_delete.html", {
        "configuracao": configuracao,
        "modo_admin": False,
        "empregado_obj": empregado,
    })


# ============================================================
# ADMIN
# ============================================================

@login_required
@admin_required
def configuracao_perfuracao_list_admin(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    configuracoes = (
        ConfiguracaoPerfuracaoEmpregado.objects
        .filter(empregado=empregado)
        .select_related("furo", "atualizado_por")
        .order_by("furo__nome")
    )

    return render(request, "projetos/configuracao_perfuracao_list_admin.html", {
        "empregado_obj": empregado,
        "configuracoes": configuracoes,
    })


@login_required
@admin_required
def configuracao_perfuracao_create_admin(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(request.POST, empregado=empregado)
        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.atualizado_por = request.user
            configuracao.save()

            messages.success(request, "Configuração de perfuração criada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_admin", pk=empregado.pk)
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(empregado=empregado)

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "titulo": f"Nova Configuração de Perfuração - {empregado.nome}",
        "modo_admin": True,
        "empregado_obj": empregado,
    })


@login_required
@admin_required
def configuracao_perfuracao_update_admin(request, pk):
    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado.objects.select_related("empregado"),
        pk=pk
    )
    empregado = configuracao.empregado

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            request.POST,
            instance=configuracao,
            empregado=empregado
        )
        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.atualizado_por = request.user
            configuracao.save()

            messages.success(request, "Configuração de perfuração atualizada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_admin", pk=empregado.pk)
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            instance=configuracao,
            empregado=empregado
        )

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "titulo": f"Editar Configuração de Perfuração - {empregado.nome}",
        "modo_admin": True,
        "empregado_obj": empregado,
        "configuracao": configuracao,
    })


@login_required
@admin_required
def configuracao_perfuracao_delete_admin(request, pk):
    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado.objects.select_related("empregado", "furo"),
        pk=pk
    )
    empregado = configuracao.empregado

    if request.method == "POST":
        configuracao.delete()
        messages.success(request, "Configuração de perfuração apagada com sucesso.")
        return redirect("projetos:configuracao_perfuracao_list_admin", pk=empregado.pk)

    return render(request, "projetos/configuracao_perfuracao_confirm_delete.html", {
        "configuracao": configuracao,
        "modo_admin": True,
        "empregado_obj": empregado,
    })

@login_required
@empregado_required
def configuracao_perfuracao_detail_empregado(request, pk):
    empregado = get_object_or_404(Empregados, user=request.user)

    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado.objects.select_related(
            "empregado", "furo", "atualizado_por"
        ),
        pk=pk,
        empregado=empregado
    )

    historicos = obter_historico_configuracao_por_configuracao(configuracao)
    ultimo_historico = obter_ultimo_historico_da_configuracao(configuracao)

    return render(request, "projetos/configuracao_perfuracao_detail.html", {
        "configuracao": configuracao,
        "historicos": historicos[:5],
        "ultimo_historico": ultimo_historico,
        "modo_admin": False,
        "empregado_obj": empregado,
    })


@login_required
@admin_required
def configuracao_perfuracao_detail_admin(request, pk):
    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado.objects.select_related(
            "empregado", "furo", "atualizado_por"
        ),
        pk=pk
    )

    historicos = obter_historico_configuracao_por_configuracao(configuracao)
    ultimo_historico = obter_ultimo_historico_da_configuracao(configuracao)

    return render(request, "projetos/configuracao_perfuracao_detail.html", {
        "configuracao": configuracao,
        "historicos": historicos[:5],
        "ultimo_historico": ultimo_historico,
        "modo_admin": True,
        "empregado_obj": configuracao.empregado,
    })