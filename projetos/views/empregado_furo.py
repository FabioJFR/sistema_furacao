from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from core.permissions import admin_required
from projetos.forms.empregado_furo import EmpregadoFuroForm
from projetos.models import Furo, EmpregadoFuro


@login_required
@admin_required
def furo_adicionar_empregado(request, furo_id):
    furo = get_object_or_404(Furo, pk=furo_id)

    if request.method == "POST":
        form = EmpregadoFuroForm(request.POST)
        if form.is_valid():
            ligacao = form.save(commit=False)
            ligacao.furo = furo
            ligacao.save()

            messages.success(request, "Trabalhador associado ao furo com sucesso.")
            return redirect("projetos:furo_detail", pk=furo.pk)
    else:
        form = EmpregadoFuroForm()

    return render(request, "projetos/furo_adicionar_empregado.html", {
        "form": form,
        "furo": furo,
        "titulo": f"Adicionar Trabalhador ao Furo {furo.nome}"
    })


@login_required
@admin_required
def furo_editar_empregado(request, pk):
    ligacao = get_object_or_404(
        EmpregadoFuro.objects.select_related("furo", "empregado"),
        pk=pk
    )

    if request.method == "POST":
        form = EmpregadoFuroForm(request.POST, instance=ligacao)
        if form.is_valid():
            form.save()
            messages.success(request, "Ligação trabalhador/furo atualizada com sucesso.")
            return redirect("projetos:furo_detail", pk=ligacao.furo.pk)
    else:
        form = EmpregadoFuroForm(instance=ligacao)

    return render(request, "projetos/furo_adicionar_empregado.html", {
        "form": form,
        "furo": ligacao.furo,
        "ligacao": ligacao,
        "titulo": f"Editar Trabalhador no Furo {ligacao.furo.nome}"
    })


@login_required
@admin_required
def furo_remover_empregado(request, pk):
    ligacao = get_object_or_404(
        EmpregadoFuro.objects.select_related("furo", "empregado"),
        pk=pk
    )
    furo = ligacao.furo

    if request.method == "POST":
        ligacao.delete()
        messages.success(request, "Trabalhador removido do furo com sucesso.")
        return redirect("projetos:furo_detail", pk=furo.pk)

    return render(request, "projetos/furo_remover_empregado.html", {
        "ligacao": ligacao,
        "furo": furo,
    })