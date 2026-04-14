from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.permissions import admin_required
from ..decorators import empregado_required

from ..models.empregado import Empregados
from ..models.projeto import Projeto
from ..models.material import Material
from ..forms.material import (
    MaterialForm,
    EntradaMaterialForm,
    SaidaMaterialForm,
    LevantamentoMaterialForm,
    DevolucaoMaterialForm,
)

from projetos.selectors.material import (
    obter_lista_materiais,
    obter_material,
    obter_contexto_material_detail,
    obter_levantamentos_empregado,
    obter_devolucoes_empregado,
    obter_levantamentos_admin,
    obter_devolucoes_admin,
)

from projetos.services.stock import (
    registrar_entrada_material,
    registrar_saida_material,
    criar_levantamento_material,
    criar_devolucao_material,
)

@login_required
@admin_required
def entrada_material_view(request, material_id):
    material = obter_material(material_id)

    if request.method == "POST":
        form = EntradaMaterialForm(request.POST)

        if form.is_valid():
            try:
                registrar_entrada_material(
                    material=material,
                    quantidade=form.cleaned_data["quantidade"],
                )
                messages.success(request, "Entrada de material registada com sucesso.")
                return redirect("materiais_lista")

            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = EntradaMaterialForm()

    context = {
        "material": material,
        "form": form,
    }

    return render(request, "projetos/entrada_material.html", context)


@login_required
@admin_required
def saida_material_view(request, material_id):
    material = obter_material(material_id)

    if request.method == "POST":
        form = SaidaMaterialForm(request.POST)

        if form.is_valid():
            try:
                registrar_saida_material(
                    material=material,
                    quantidade=form.cleaned_data["quantidade"],
                )
                messages.success(request, "Saída de material registada com sucesso.")
                return redirect("materiais_lista")

            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = SaidaMaterialForm()

    context = {
        "material": material,
        "form": form,
    }

    return render(request, "projetos/saida_material.html", context)

# ---------------- MATERIAIS ----------------
@login_required
@admin_required
def material_list(request):
    materiais = obter_lista_materiais()
    return render(request, 'projetos/material_list.html', {
        'materiais': materiais
    })


@login_required
@admin_required
def material_detail(request, material_id):
    context = obter_contexto_material_detail(material_id)
    return render(request, 'projetos/material_detail.html', context)


@login_required
@admin_required
def material_create(request):
    if request.method == "POST":
        form = MaterialForm(request.POST)
        if form.is_valid():
            material = form.save()
            messages.success(request, "Material criado com sucesso.")
            return redirect('projetos:material_detail', material_id=material.id)
        else:
            messages.error(request, "Erro ao criar o material. Verifique os dados.")
    else:
        form = MaterialForm()

    return render(request, 'projetos/material_form.html', {
        'form': form,
        'titulo': 'Novo Material'
    })


@login_required
@admin_required
def material_update(request, material_id):
    material = get_object_or_404(Material, id=material_id)

    if request.method == "POST":
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, "Material atualizado com sucesso.")
            return redirect('projetos:material_detail', material_id=material.id)
        else:
            messages.error(request, "Erro ao atualizar o material. Verifique os dados.")
    else:
        form = MaterialForm(instance=material)

    return render(request, 'projetos/material_form.html', {
        'form': form,
        'titulo': 'Editar Material',
        'material': material
    })


@login_required
@admin_required
def material_delete(request, material_id):
    material = get_object_or_404(Material, id=material_id)

    if request.method == "POST":
        material.delete()
        messages.success(request, "Material apagado com sucesso.")
        return redirect('projetos:material_list')

    return render(request, 'projetos/material_confirm_delete.html', {
        'material': material
    })

# ------------ Levantamento Materiais ----------------- #

@login_required
@empregado_required
def levantamento_material_create(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    if request.method == "POST":
        form = LevantamentoMaterialForm(request.POST, empregado=empregado)
        if form.is_valid():
            criar_levantamento_material(form, empregado)
            messages.success(request, "Levantamento de material registado com sucesso.")
            return redirect('projetos:levantamento_material_list')

            messages.success(request, "Levantamento de material registado com sucesso.")
            return redirect('projetos:levantamento_material_list')
        else:
            messages.error(request, "Erro ao registar o levantamento. Verifique os dados.")
    else:
        form = LevantamentoMaterialForm(
            empregado=empregado,
            initial={'data': timezone.now().date()}
        )

    return render(request, "projetos/levantamento_material_form.html", {
        "form": form,
        "titulo": "Levantar Material"
    })


@login_required
@empregado_required
def levantamento_material_list(request):
    empregado = get_object_or_404(Empregados, user=request.user)
    levantamentos = obter_levantamentos_empregado(empregado)

    return render(request, "projetos/levantamento_material_list.html", {
        "levantamentos": levantamentos
    })

@login_required
@admin_required
def levantamento_material_admin_list(request):
    levantamentos = obter_levantamentos_admin()

    empregado_id = request.GET.get('empregado')
    material_id = request.GET.get('material')
    projeto_id = request.GET.get('projeto')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if empregado_id:
        levantamentos = levantamentos.filter(empregado_id=empregado_id)

    if material_id:
        levantamentos = levantamentos.filter(material_id=material_id)

    if projeto_id:
        levantamentos = levantamentos.filter(projeto_id=projeto_id)

    if data_inicio:
        levantamentos = levantamentos.filter(data__gte=parse_date(data_inicio))

    if data_fim:
        levantamentos = levantamentos.filter(data__lte=parse_date(data_fim))

    empregados = Empregados.objects.all().order_by('nome')
    materiais = Material.objects.all().order_by('nome')
    projetos = Projeto.objects.all().order_by('nome')

    return render(request, "projetos/levantamento_material_admin_list.html", {
        "levantamentos": levantamentos,
        "empregados": empregados,
        "materiais": materiais,
        "projetos": projetos,
        "filtros": {
            "empregado": empregado_id or "",
            "material": material_id or "",
            "projeto": projeto_id or "",
            "data_inicio": data_inicio or "",
            "data_fim": data_fim or "",
        }
    })

# ----------- Devolução MAteriais -----------------------#

@login_required
@empregado_required
def devolucao_material_create(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    if request.method == "POST":
        form = DevolucaoMaterialForm(request.POST, empregado=empregado)
        if form.is_valid():
            criar_devolucao_material(form, empregado)
            messages.success(request, "Devolução de material registada com sucesso.")
            return redirect('projetos:devolucao_material_list')

            messages.success(request, "Devolução de material registada com sucesso.")
            return redirect('projetos:devolucao_material_list')
        else:
            messages.error(request, "Erro ao registar a devolução. Verifique os dados.")
    else:
        form = DevolucaoMaterialForm(
            empregado=empregado,
            initial={'data': timezone.now().date()}
        )

    return render(request, "projetos/devolucao_material_form.html", {
        "form": form,
        "titulo": "Devolver Material"
    })


@login_required
@empregado_required
def devolucao_material_list(request):
    empregado = get_object_or_404(Empregados, user=request.user)
    devolucoes = obter_devolucoes_empregado(empregado)

    return render(request, "projetos/devolucao_material_list.html", {
        "devolucoes": devolucoes
    })

@login_required
@admin_required
def devolucao_material_admin_list(request):
    devolucoes = obter_devolucoes_admin()

    return render(request, "projetos/devolucao_material_admin_list.html", {
        "devolucoes": devolucoes
    })
