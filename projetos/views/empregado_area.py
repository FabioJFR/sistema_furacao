from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from projetos.decorators import empregado_required
from projetos.forms.empregado_area import MeusDadosEmpregadoForm
from projetos.models import (
    ConfiguracaoPerfuracaoEmpregado,
    DevolucaoMaterial,
    Empregados,
    LevantamentoMaterial,
    RegistoDiarioEmpregado,
)


@login_required
@empregado_required
def meus_dados_empregado(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    projetos_historico = (
        empregado.ligacoes_projetos
        .select_related("projeto")
        .all()
        .order_by("-ativo", "-data_inicio")
    )

    furos_resumo = (
        RegistoDiarioEmpregado.objects
        .filter(empregado=empregado, furo__isnull=False)
        .values("furo__id", "furo__nome", "projeto__nome")
        .annotate(
            total_metros=Sum("metros_furados"),
            total_horas=Sum("horas_trabalhadas"),
        )
        .order_by("-total_metros", "furo__nome")
    )

    context = {
        "empregado": empregado,
        "projetos_historico": projetos_historico,
        "furos_resumo": furos_resumo,
        "total_registos": RegistoDiarioEmpregado.objects.filter(empregado=empregado).count(),
        "total_levantamentos": LevantamentoMaterial.objects.filter(empregado=empregado).count(),
        "total_devolucoes": DevolucaoMaterial.objects.filter(empregado=empregado).count(),
        "total_configuracoes": ConfiguracaoPerfuracaoEmpregado.objects.filter(empregado=empregado).count(),
    }

    return render(request, "projetos/meus_dados_empregado.html", context)


@login_required
@empregado_required
def meus_dados_empregado_editar(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    if request.method == "POST":
        form = MeusDadosEmpregadoForm(
            request.POST,
            request.FILES,
            instance=empregado,
        )
        if form.is_valid():
            empregado = form.save(commit=False)
            empregado.user = request.user
            empregado.save()

            messages.success(request, "Os teus dados foram atualizados com sucesso.")
            return redirect("projetos:meus_dados_empregado")

        messages.error(request, "Erro ao atualizar os teus dados.")
    else:
        form = MeusDadosEmpregadoForm(instance=empregado)

    return render(request, "projetos/meus_dados_empregado_editar.html", {
        "empregado": empregado,
        "form": form,
    })