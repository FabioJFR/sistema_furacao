import math

import plotly.graph_objects as go
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions import admin_required
from projetos.selectors.projetos import (
    obter_contexto_projeto_detail,
    obter_dados_3d_projeto,
    obter_furos_projeto,
    obter_lista_projetos,
    obter_projeto,
)
from projetos.services.projetos import atualizar_projeto, criar_projeto
from projetos.utils.tragetoria import calcular_trajetoria_min_curv

from ..forms.projeto import ProjetoForm
from ..models.projeto import Projeto


# ----------------- Globo ------------------------------ #
@login_required
@admin_required
def globo_projetos(request):
    projetos = Projeto.objects.exclude(
        localizacao_lat__isnull=True
    ).exclude(
        localizacao_lon__isnull=True
    )

    lats = [p.localizacao_lat for p in projetos]
    lons = [p.localizacao_lon for p in projetos]
    nomes = [p.nome for p in projetos]

    fig = go.Figure(data=[go.Scattergeo(
        lat=lats,
        lon=lons,
        text=nomes,
        mode="markers",
    )])

    graph = fig.to_html(full_html=False)

    return render(request, "projetos/globo.html", {"graph": graph})


# ---------------- PROJETOS ----------------
@login_required
@admin_required
def projeto_list(request):
    projetos_qs = obter_lista_projetos()
    projetos_serializaveis = list(projetos_qs.values(
        "id", "pk", "nome", "cliente", "cidade", "pais", "localizacao_lat", "localizacao_lon"
    ))
    context = {"projetos": projetos_serializaveis}
    return render(request, "projetos/projeto_list.html", context)


@login_required
@admin_required
def projeto_update(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)
    form = ProjetoForm(request.POST or None, instance=projeto)

    if request.method == "POST":
        if form.is_valid():
            projeto = atualizar_projeto(form)
            messages.success(request, "Projeto atualizado com sucesso.")
            return redirect("projetos:projeto_detail", pk=projeto.pk)
        messages.error(request, "Erro ao atualizar o projeto. Verifique os dados.")

    return render(request, "projetos/projeto_editar.html", {
        "form": form,
        "projeto": projeto,
    })


@login_required
@admin_required
def projeto_create(request):
    if request.method == "POST":
        form = ProjetoForm(request.POST)
        if form.is_valid():
            criar_projeto(form)
            messages.success(request, "Projeto criado com sucesso.")
            return redirect("projetos:projeto_list")

        messages.error(request, "Erro ao criar o projeto. Verifique os dados.")
    else:
        form = ProjetoForm()

    return render(request, "projetos/projeto_form.html", {"form": form})


@login_required
@admin_required
def projeto_delete(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)

    if request.method == "POST":
        projeto.delete()
        return redirect("projetos:projeto_list")

    return render(request, "projetos/projeto_confirm_delete.html", {
        "projeto": projeto,
    })


@login_required
@admin_required
def projeto_detail(request, pk):
    context = obter_contexto_projeto_detail(pk)
    return render(request, "projetos/projeto_detail.html", context)


# ---------------- 3D ----------------
@login_required
@admin_required
def projeto_3d(request, pk):
    projeto = obter_projeto(pk)
    furos = obter_furos_projeto(projeto)
    furos_3d = obter_dados_3d_projeto(projeto)

    fig = go.Figure()

    for furo in furos:
        medicoes = list(furo.medicoes.all().order_by("profundidade_medida"))

        # -----------------------------------
        # CASO 1: FURO COM MEDIÇÕES REAIS
        # -----------------------------------
        if medicoes:
            origem = (
                float(furo.origem_este or 0.0),
                float(furo.origem_norte or 0.0),
                float(furo.origem_tvd or 0.0),
            )

            pontos, doglegs, alertas = calcular_trajetoria_min_curv(
                medicoes,
                origem=origem,
            )

            x = [p[0] for p in pontos]
            y = [p[1] for p in pontos]
            z = [p[2] for p in pontos]

            fig.add_trace(go.Scatter3d(
                x=x,
                y=y,
                z=z,
                mode="lines+markers",
                name=furo.nome,
                line=dict(width=6),
                marker=dict(size=4),
                text=[furo.nome] * len(x),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "X: %{x:.2f}<br>"
                    "Y: %{y:.2f}<br>"
                    "Z: %{z:.2f}<extra></extra>"
                ),
            ))
            continue

        # -----------------------------------
        # CASO 2: FURO SEM MEDIÇÕES
        # FALLBACK SIMPLES
        # -----------------------------------
        origem_este = float(furo.origem_este or 0)
        origem_norte = float(furo.origem_norte or 0)
        origem_tvd = float(furo.origem_tvd or 0)

        profundidade = (
            float(furo.profundidade_maxima_atingida or 0)
            or float(furo.profundidade_atual or 0)
            or float(furo.profundidade_alvo_atual or 0)
            or float(furo.profundidade_alvo_inicial or 0)
            or float(furo.profundidade_inicial or 0)
        )

        inclinacao = float(
            furo.inclinacao_real_atual
            or furo.inclinacao_planeada_atual
            or furo.inclinacao_planeada_inicial
            or 0
        )
        azimute = float(
            furo.azimute_real_atual
            or furo.azimute_planeado_atual
            or furo.azimute_planeado_inicial
            or 0
        )

        inc_rad = math.radians(abs(inclinacao))
        azi_rad = math.radians(azimute)

        desloc_horizontal = profundidade * math.sin(inc_rad)
        delta_x = desloc_horizontal * math.sin(azi_rad)
        delta_y = desloc_horizontal * math.cos(azi_rad)
        delta_z = profundidade * math.cos(inc_rad)

        x = [origem_este, origem_este + delta_x]
        y = [origem_norte, origem_norte + delta_y]
        z = [origem_tvd, origem_tvd - delta_z]

        fig.add_trace(go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode="lines+markers",
            name=furo.nome,
            line=dict(width=4, dash="dash"),
            marker=dict(size=3),
            text=[furo.nome, furo.nome],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "X: %{x:.2f}<br>"
                "Y: %{y:.2f}<br>"
                "Z: %{z:.2f}<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=f"Visualização 3D - {projeto.nome}",
        scene=dict(
            xaxis_title="Este",
            yaxis_title="Norte",
            zaxis_title="TVD / Profundidade",
            zaxis=dict(autorange="reversed"),
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        height=700,
    )

    graph = fig.to_html(full_html=False)

    context = {
        "projeto": projeto,
        "furos": furos,
        "furos_3d": furos_3d,
        "graph": graph,
    }

    return render(request, "projetos/projeto_3d.html", context)