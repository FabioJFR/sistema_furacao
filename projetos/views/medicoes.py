from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..decorators import admin_required
from ..forms.medicao import MedicaoForm
from ..models.furo import Furo

from projetos.selectors.medicoes import (
    obter_lista_medicoes,
    obter_medicao,
)
from projetos.services.medicoes import (
    criar_medicao,
    atualizar_medicao,
)


@login_required
@admin_required
def medicao_list(request):
    medicoes = obter_lista_medicoes()

    return render(
        request,
        "projetos/medicao_list.html",
        {"medicoes": medicoes},
    )


@login_required
@admin_required
def medicao_create(request, furo_id):
    furo = get_object_or_404(Furo, pk=furo_id)

    if request.method == "POST":
        form = MedicaoForm(request.POST, request.FILES, furo=furo)
        if form.is_valid():
            criar_medicao(form, furo=furo)
            messages.success(request, "Medição criada com sucesso.")
            return redirect("projetos:furo_detail", pk=furo.pk)

        messages.error(request, "Erro ao criar a medição. Verifique os dados.")
    else:
        form = MedicaoForm(furo=furo)

    return render(
        request,
        "projetos/medicao_form.html",
        {
            "form": form,
            "titulo": f"Nova Medição - {furo.nome}",
            "furo": furo,
        },
    )


@login_required
@admin_required
def medicao_update(request, pk):
    medicao = obter_medicao(pk)

    if request.method == "POST":
        form = MedicaoForm(
            request.POST,
            request.FILES,
            instance=medicao,
            furo=medicao.furo,
        )
        if form.is_valid():
            atualizar_medicao(form)
            messages.success(request, "Medição atualizada com sucesso.")
            return redirect("projetos:medicao_list")

        messages.error(request, "Erro ao atualizar a medição. Verifique os dados.")
    else:
        form = MedicaoForm(instance=medicao, furo=medicao.furo)

    return render(
        request,
        "projetos/medicao_form.html",
        {
            "form": form,
            "titulo": f"Editar Medição - {medicao.furo.nome}",
            "medicao": medicao,
            "furo": medicao.furo,
        },
    )


@login_required
@admin_required
def medicao_delete(request, pk):
    medicao = obter_medicao(pk)

    if request.method == "POST":
        furo = medicao.furo
        medicao.delete()
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