import math

import plotly.graph_objects as go
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..decorators import admin_required, empregado_required
from ..forms.furo import FuroCreateForm, FuroForm
from ..forms.medicao import MedicaoForm
from ..models.empregado import Empregados
from ..models.furo import Furo
from ..models.medicao import Medicao
from ..models.registo import RegistoDiarioEmpregado
from ..utils.tragetoria import calcular_linha_planeada
from projetos.selectors.furos import (
    obter_contexto_detalhe_furo,
    obter_equipa_e_configuracao_por_furo,
    obter_furo,
    obter_lista_furos,
)
from projetos.services.furos import (
    criar_furo,
    criar_medicao_para_furo,
)
from projetos.utils.tragetoria import calcular_trajetoria_min_curv


# ---------------- FUROS ----------------
@login_required
@empregado_required
def furo_detail_empregado(request, pk):
    empregado = get_object_or_404(Empregados, user=request.user)
    furo = get_object_or_404(Furo, pk=pk)

    trabalhou_no_furo = empregado.registos_diarios.filter(furo=furo).exists()
    if not trabalhou_no_furo:
        return render(request, "projetos/sem_permissao.html", status=403)

    registos_furo = (
        RegistoDiarioEmpregado.objects
        .filter(furo=furo)
        .select_related("empregado", "projeto", "furo")
        .order_by("-data", "-criado_em")
    )

    medicoes_furo = (
        Medicao.objects
        .filter(furo=furo)
        .order_by("-data_modificacao", "-profundidade_medida")
    )

    return render(request, "projetos/furo_detail_empregado.html", {
        "empregado": empregado,
        "furo": furo,
        "registos_furo": registos_furo,
        "medicoes_furo": medicoes_furo,
    })


@login_required
@admin_required
def furo_create(request):
    if request.method == "POST":
        form = FuroCreateForm(request.POST)
        if form.is_valid():
            furo = criar_furo(form)

            messages.success(request, "Furo criado com sucesso.")
            return redirect("projetos:furo_detail", pk=furo.pk)

        messages.error(request, "Erro ao criar o furo. Verifique os dados.")
    else:
        form = FuroCreateForm()

    return render(request, "projetos/form.html", {
        "form": form,
        "titulo": "Criar Novo Furo",
    })


@login_required
@admin_required
def furo_detail(request, pk):
    context = obter_contexto_detalhe_furo(pk)
    furo = context["furo"]

    if request.method == "POST":
        form = MedicaoForm(request.POST, request.FILES, furo=furo)
        if form.is_valid():
            criar_medicao_para_furo(form, furo)
            messages.success(request, "Medição registrada com sucesso!")
            return redirect("projetos:furo_detail", pk=furo.pk)

        messages.error(request, "Erro ao registrar medição. Verifique os dados.")
    else:
        form = MedicaoForm(furo=furo)

    context["form"] = form
    context["configuracoes"] = obter_equipa_e_configuracao_por_furo(furo)

    return render(request, "projetos/furo_detail.html", context)


@login_required
@admin_required
def furo_list(request):
    furos = obter_lista_furos()
    return render(request, "projetos/furo_list.html", {"furos": furos})


@login_required
@admin_required
def furo_update(request, pk):
    furo = get_object_or_404(Furo, pk=pk)

    if request.method == "POST":
        form = FuroForm(request.POST, instance=furo)
        if form.is_valid():
            furo = form.save(commit=False)

            if furo.profundidade_atual and furo.profundidade_maxima_atingida:
                if furo.profundidade_atual > furo.profundidade_maxima_atingida:
                    furo.profundidade_maxima_atingida = furo.profundidade_atual

            if not furo.medicoes.exists():
                furo.profundidade_atual = 0.0
                furo.profundidade_maxima_atingida = 0.0

            furo.origem_este = furo.origem_este or 0.0
            furo.origem_norte = furo.origem_norte or 0.0
            furo.origem_tvd = furo.origem_tvd or 0.0

            furo.save()

            messages.success(request, "Furo atualizado com sucesso.")
            return redirect("projetos:furo_detail", pk=furo.pk)

        messages.error(request, "Erro ao atualizar o furo. Verifique os dados.")
        print("ERROS DO FORM:", form.errors)
    else:
        form = FuroForm(instance=furo)

    return render(request, "projetos/furo_update.html", {
        "form": form,
        "furo": furo,
    })


@login_required
@admin_required
def furo_delete(request, pk):
    furo = get_object_or_404(Furo, pk=pk)
    if request.method == "POST":
        furo.delete()
        return redirect("projetos:furo_list")
    return render(request, "projetos/furo_confirm_delete.html", {"furo": furo})


@login_required
def furo_3d_geologico(request, furo_id):
    furo = obter_furo(furo_id)

    is_admin = request.user.is_superuser or request.user.groups.filter(
        name="Administradores"
    ).exists()

    if not is_admin:
        empregado = get_object_or_404(Empregados, user=request.user)

        trabalhou_no_furo = RegistoDiarioEmpregado.objects.filter(
            empregado=empregado,
            furo=furo,
        ).exists()

        if not trabalhou_no_furo:
            messages.error(request, "Não tens permissão para ver o 3D deste furo.")
            return redirect("projetos:area_empregado")

    medicoes = list(furo.medicoes.all().order_by("profundidade_medida"))

    if not medicoes:
        messages.warning(request, "Este furo ainda não possui medições.")
        return render(request, "projetos/furo_3d.html", {
            "furo": furo,
            "graph": None,
            "numero_medicoes": 0,
            "profundidade_final": 0.0,
            "dogleg_max": 0.0,
            "estado_max": "OK",
        })

    origem = (
        float(furo.origem_este or 0.0),
        float(furo.origem_norte or 0.0),
        float(furo.origem_tvd or 0.0),
    )

    pontos, doglegs, alertas = calcular_trajetoria_min_curv(
        medicoes,
        origem=origem,
    )

    ultima_md = float(medicoes[-1].profundidade_medida or 0.0)
    profundidade_planeada_final = float(
        furo.profundidade_alvo_atual
        or furo.profundidade_alvo_inicial
        or furo.profundidade_maxima_atingida
        or furo.profundidade_atual
        or 0.0
    )

    inclinacao_planeada = float(
        furo.inclinacao_planeada_atual
        or furo.inclinacao_planeada_inicial
        or 0.0
    )
    azimute_planeado = float(
        furo.azimute_planeado_atual
        or furo.azimute_planeado_inicial
        or 0.0
    )

    linha_planeada_atual = calcular_linha_planeada(
        origem=origem,
        inclinacao=inclinacao_planeada,
        azimute=azimute_planeado,
        comprimento=ultima_md,
    )

    linha_planeada_final = calcular_linha_planeada(
        origem=origem,
        inclinacao=inclinacao_planeada,
        azimute=azimute_planeado,
        comprimento=profundidade_planeada_final,
    )

    x, y, z = [], [], []
    customdata = []

    if pontos:
        x.append(pontos[0][0])
        y.append(pontos[0][1])
        z.append(pontos[0][2])
        customdata.append([0.0, 0.0, 0.0, 0.0, None, "ORIGEM"])

    total_pontos_medicoes = min(len(medicoes), max(len(pontos) - 1, 0))

    for idx in range(total_pontos_medicoes):
        med = medicoes[idx]
        x_coord, y_coord, z_coord = pontos[idx + 1]

        prof = float(med.profundidade_medida or 0.0)
        incl = float(med.inclinacao_real_medida or 0.0)
        azim = float(med.azimute_real_medido or 0.0)
        mag = float(med.magnetismo or 0.0)
        img_url = med.imagem.url if med.imagem else None
        estado = alertas[idx + 1] if idx + 1 < len(alertas) else "OK"

        x.append(x_coord)
        y.append(y_coord)
        z.append(z_coord)

        customdata.append([
            prof,
            incl,
            azim,
            mag,
            img_url,
            estado,
        ])

    cores_pontos = [0.0]
    for idx in range(total_pontos_medicoes):
        if idx + 1 < len(doglegs):
            cores_pontos.append(doglegs[idx + 1])
        else:
            cores_pontos.append(0.0)

    seta_tracos = []
    passo_setas = max(5, len(x) // 8)

    for i in range(1, len(x)):
        if i % passo_setas != 0:
            continue

        x0, y0, z0 = x[i - 1], y[i - 1], z[i - 1]
        x1, y1, z1 = x[i], y[i], z[i]

        seta_tracos.append(go.Cone(
            x=[x0],
            y=[y0],
            z=[z0],
            u=[x1 - x0],
            v=[y1 - y0],
            w=[z1 - z0],
            sizemode="absolute",
            sizeref=1,
            anchor="tail",
            colorscale="Viridis",
            opacity=0.6,
            showscale=False,
            hoverinfo="skip",
        ))

    tubo = go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode="lines",
        line=dict(
            width=14,
            color="rgba(52, 152, 219, 0.6)",
        ),
        hoverinfo="skip",
        showlegend=False,
    )

    scatter = go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode="lines+markers",
        line=dict(width=5, color="blue"),
        marker=dict(
            size=8,
            color=cores_pontos,
            colorscale=[
                [0, "green"],
                [0.5, "yellow"],
                [1, "red"],
            ],
            colorbar=dict(
                title="Dogleg",
                len=0.6,
                thickness=12,
                x=1.08,
                y=0.45,
            ),
            showscale=True,
        ),
        customdata=customdata,
        hovertemplate=(
            "Trajetória real<br>"
            "MD: %{customdata[0]:.2f} m<br>"
            "Inclinação: %{customdata[1]:.2f}°<br>"
            "Azimute: %{customdata[2]:.2f}°<br>"
            "Magnetismo: %{customdata[3]:.2f}<br>"
            "Estado: %{customdata[5]}<br>"
            "Este: %{x:.2f} m<br>"
            "Norte: %{y:.2f} m<br>"
            "TVD: %{z:.2f} m<br>"
            "<extra></extra>"
        ),
        name="Trajetória real",
    )

    planeado_ultima_trace = go.Scatter3d(
        x=linha_planeada_atual["x"],
        y=linha_planeada_atual["y"],
        z=linha_planeada_atual["z"],
        mode="lines",
        name="Planeado até última medição",
        line=dict(
            width=5,
            color="orange",
            dash="dash",
        ),
        hovertemplate=(
            "Trajetória planeada<br>"
            f"Até última medição<br>"
            f"MD alvo: {ultima_md:.2f} m<br>"
            "Este: %{x:.2f} m<br>"
            "Norte: %{y:.2f} m<br>"
            "TVD: %{z:.2f} m<br>"
            "<extra></extra>"
        ),
    )

    planeado_final_trace = go.Scatter3d(
        x=linha_planeada_final["x"],
        y=linha_planeada_final["y"],
        z=linha_planeada_final["z"],
        mode="lines",
        name="Planeado final",
        line=dict(
            width=5,
            color="gray",
            dash="dot",
        ),
        hovertemplate=(
            "Trajetória planeada<br>"
            "Até profundidade final<br>"
            f"MD alvo: {profundidade_planeada_final:.2f} m<br>"
            "Este: %{x:.2f} m<br>"
            "Norte: %{y:.2f} m<br>"
            "TVD: %{z:.2f} m<br>"
            "<extra></extra>"
        ),
    )

    fig = go.Figure(
        data=[tubo, scatter, planeado_ultima_trace, planeado_final_trace] + seta_tracos
    )

    dogleg_max = max(doglegs) if doglegs else 0.0
    estado_max = "OK"
    if any(a == "CRÍTICO" for a in alertas):
        estado_max = "CRÍTICO"
    elif any(a == "ATENÇÃO" for a in alertas):
        estado_max = "ATENÇÃO"

    profundidade_final = medicoes[-1].profundidade_medida if medicoes else 0.0

    fig.update_layout(
        scene=dict(
            xaxis_title="Este (m)",
            yaxis_title="Norte (m)",
            zaxis_title="TVD / Profundidade Vertical (m)",
            zaxis=dict(autorange="reversed"),
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=0.7),
            camera=dict(
                eye=dict(x=1.8, y=1.8, z=1.2),
            ),
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.95,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="lightgray",
            borderwidth=1,
            font=dict(size=11),
        ),
        margin=dict(l=0, r=140, t=20, b=0),
        height=800,
    )

    graph = fig.to_html(full_html=False)

    return render(request, "projetos/furo_3d.html", {
        "furo": furo,
        "graph": graph,
        "numero_medicoes": len(medicoes),
        "profundidade_final": profundidade_final or 0.0,
        "dogleg_max": dogleg_max,
        "estado_max": estado_max,
    })