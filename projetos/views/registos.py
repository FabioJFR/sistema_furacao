from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.permissions import admin_required
from ..decorators import empregado_required

from projetos.models import (
    Empregados,
    Projeto,
    Furo,
    RegistoDiarioEmpregado,
    RegistoDiarioFotoAmostra,
)
from projetos.forms.registo import (
    RegistoDiarioEmpregadoAdminForm,
    RegistoDiarioEmpregadoForm,
)
from projetos.services.registos import criar_registo_diario, atualizar_registo_diario
from ..services.empregados import recalcular_resumo_empregado
from ..services.furos import recalcular_resumo_furo


# -------- REGISTOS --------------


def criar_registo_view(request):
    if request.method == "POST":
        try:
            empregado = request.user.empregado
            projeto_id = request.POST.get("projeto")
            furo_id = request.POST.get("furo")

            data = request.POST.get("data")
            metros = request.POST.get("metros_furados") or 0
            horas = request.POST.get("horas_trabalhadas") or 0

            projeto = Projeto.objects.get(pk=projeto_id)
            furo = Furo.objects.get(pk=furo_id)

            criar_registo_diario(
                empregado=empregado,
                projeto=projeto,
                furo=furo,
                data=data,
                metros_furados=metros,
                horas_trabalhadas=horas,
            )

            messages.success(request, "Registo criado com sucesso.")
        except Exception as e:
            messages.error(request, f"Erro ao criar registo: {e}")

    return redirect("projetos:area_empregado")


@login_required
@empregado_required
def registo_diario_list(request):
    empregado = get_object_or_404(Empregados, user=request.user)
    registos = empregado.registos_diarios.select_related("projeto", "furo").all()

    return render(
        request,
        "projetos/registo_diario_list.html",
        {
            "empregado": empregado,
            "registos": registos,
        },
    )


@login_required
@empregado_required
def registo_diario_create(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    if request.method == "POST":
        form = RegistoDiarioEmpregadoForm(
            request.POST,
            request.FILES,
            empregado=empregado,
        )

        if form.is_valid():
            registo = criar_registo_diario(form=form, empregado=empregado)

            fotos_amostra = request.FILES.getlist("fotos_amostra")
            for foto in fotos_amostra:
                RegistoDiarioFotoAmostra.objects.create(
                    registo=registo,
                    imagem=foto,
                )

            messages.success(request, "Registo diário guardado com sucesso.")
            return redirect("projetos:area_empregado")

        messages.error(request, "Erro ao guardar o registo diário. Verifique os dados.")
    else:
        form = RegistoDiarioEmpregadoForm(
            empregado=empregado,
            initial={"data": timezone.now().date()},
        )

    return render(
        request,
        "projetos/registo_diario_form.html",
        {
            "form": form,
            "empregado": empregado,
            "titulo": "Novo Registo Diário",
        },
    )


@login_required
@empregado_required
def registo_diario_update(request, pk):
    empregado = get_object_or_404(Empregados, user=request.user)
    registo = get_object_or_404(RegistoDiarioEmpregado, pk=pk, empregado=empregado)

    furo_antigo = registo.furo

    if request.method == "POST":
        form = RegistoDiarioEmpregadoForm(
            request.POST,
            request.FILES,
            instance=registo,
            empregado=empregado,
        )

        if form.is_valid():
            registo = form.save(commit=False)
            registo.editado_por_empregado = True
            registo.editado_em = timezone.now()
            registo.save()

            fotos_amostra = request.FILES.getlist("fotos_amostra")
            for foto in fotos_amostra:
                RegistoDiarioFotoAmostra.objects.create(
                    registo=registo,
                    imagem=foto,
                )

            recalcular_resumo_empregado(empregado)

            if furo_antigo:
                recalcular_resumo_furo(furo_antigo)

            if registo.furo:
                recalcular_resumo_furo(registo.furo)

            messages.success(request, "Registo diário atualizado com sucesso.")
            return redirect("projetos:registo_diario_list")

        messages.error(request, "Erro ao atualizar o registo diário.")
    else:
        form = RegistoDiarioEmpregadoForm(instance=registo, empregado=empregado)

    return render(
        request,
        "projetos/registo_diario_form.html",
        {
            "form": form,
            "empregado": empregado,
            "titulo": "Editar Registo Diário",
            "registo": registo,
        },
    )


@login_required
@admin_required
def registos_admin_list(request):
    registos = RegistoDiarioEmpregado.objects.select_related(
        "empregado",
        "projeto",
        "furo",
    ).all()

    empregado_id = request.GET.get("empregado")
    projeto_id = request.GET.get("projeto")
    furo_id = request.GET.get("furo")
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    if empregado_id:
        registos = registos.filter(empregado_id=empregado_id)

    if projeto_id:
        registos = registos.filter(projeto_id=projeto_id)

    if furo_id:
        registos = registos.filter(furo_id=furo_id)

    if data_inicio:
        data_inicio_parsed = parse_date(data_inicio)
        if data_inicio_parsed:
            registos = registos.filter(data__gte=data_inicio_parsed)

    if data_fim:
        data_fim_parsed = parse_date(data_fim)
        if data_fim_parsed:
            registos = registos.filter(data__lte=data_fim_parsed)

    totais = registos.aggregate(
        total_horas=Sum("horas_trabalhadas"),
        total_metros=Sum("metros_furados"),
        total_paragem=Sum("horas_paragem"),
    )

    empregados = Empregados.objects.all().order_by("nome")
    projetos = Projeto.objects.all().order_by("nome")
    furos = Furo.objects.all().order_by("nome")

    return render(
        request,
        "projetos/registos_admin_list.html",
        {
            "registos": registos,
            "empregados": empregados,
            "projetos": projetos,
            "furos": furos,
            "filtros": {
                "empregado": empregado_id or "",
                "projeto": projeto_id or "",
                "furo": furo_id or "",
                "data_inicio": data_inicio or "",
                "data_fim": data_fim or "",
            },
            "total_horas": totais["total_horas"] or 0,
            "total_metros": totais["total_metros"] or 0,
            "total_paragem": totais["total_paragem"] or 0,
        },
    )


@login_required
@admin_required
def registo_admin_update(request, pk):
    registo = get_object_or_404(RegistoDiarioEmpregado, pk=pk)

    if request.method == "POST":
        form = RegistoDiarioEmpregadoAdminForm(
            request.POST,
            request.FILES,
            instance=registo,
        )

        if form.is_valid():
            atualizar_registo_diario(registo, form)

            fotos_amostra = request.FILES.getlist("fotos_amostra")
            for foto in fotos_amostra:
                RegistoDiarioFotoAmostra.objects.create(
                    registo=registo,
                    imagem=foto,
                )

            messages.success(request, "Registo corrigido com sucesso.")
            return redirect("projetos:registos_admin_list")

        messages.error(request, "Erro ao corrigir o registo.")
    else:
        form = RegistoDiarioEmpregadoAdminForm(instance=registo)

    return render(
        request,
        "projetos/registo_admin_form.html",
        {
            "form": form,
            "registo": registo,
            "titulo": "Corrigir Registo de Produção",
        },
    )