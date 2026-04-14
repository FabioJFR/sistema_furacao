from django.shortcuts import render, get_object_or_404, redirect
from ..models.maquina import Maquina
from ..forms.maquina import MaquinaForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..decorators import admin_required, empregado_required
from projetos.selectors.maquinas import (
    obter_lista_maquinas,
    obter_maquina,
    obter_contexto_maquina_detail,
)

from projetos.services.maquinas import (
    criar_maquina,
    atualizar_maquina,
)

# ---------------- MAQUINAS ----------------
@login_required
@admin_required
def maquina_list(request):
    maquinas = obter_lista_maquinas()
    return render(request, "projetos/maquina_list.html", {
        "maquinas": maquinas
    })


@login_required
@admin_required
def maquina_detail(request, maquina_id):
    context = obter_contexto_maquina_detail(maquina_id)
    return render(request, "projetos/maquina_detail.html", context)


@login_required
@admin_required
def maquina_create(request):
    if request.method == "POST":
        form = MaquinaForm(request.POST)
        if form.is_valid():
            maquina = criar_maquina(form)
            messages.success(request, "Máquina criada com sucesso.")
            return redirect('projetos:maquina_detail', maquina_id=maquina.id)
        else:
            messages.error(request, "Erro ao criar a máquina. Verifique os dados.")
    else:
        form = MaquinaForm()

    return render(request, 'projetos/maquina_form.html', {
        'form': form,
        'titulo': 'Nova Máquina'
    })


@login_required
@admin_required
def maquina_update(request, maquina_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)

    if request.method == "POST":
        form = MaquinaForm(request.POST, instance=maquina)
        if form.is_valid():
            atualizar_maquina(form)
            messages.success(request, "Máquina atualizada com sucesso.")
            return redirect('projetos:maquina_detail', maquina_id=maquina.id)
        else:
            messages.error(request, "Erro ao atualizar a máquina. Verifique os dados.")
    else:
        form = MaquinaForm(instance=maquina)

    return render(request, 'projetos/maquina_form.html', {
        'form': form,
        'titulo': 'Editar Máquina',
        'maquina': maquina
    })


@login_required
@admin_required
def maquina_delete(request, maquina_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)

    if request.method == "POST":
        maquina.delete()
        messages.success(request, "Máquina apagada com sucesso.")
        return redirect('projetos:maquina_list')

    return render(request, 'projetos/maquina_confirm_delete.html', {
        'maquina': maquina
    })