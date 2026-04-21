import logging
import math

import plotly.graph_objects as go
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..decorators import admin_required, empregado_required
from ..forms.furo import FuroCreateForm, FuroForm
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
from projetos.services.furos import criar_furo
from projetos.utils.tragetoria import calcular_trajetoria_min_curv

from geologia.models import LogGeologicoFuro, MissaoDroneFuro
from plataforma.models import PerfilPlataforma

logger = logging.getLogger("core")



ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


# ---------------- HELPERS ----------------
def _obter_contexto_admin_furos(request):
    logger.debug(
        "A resolver contexto administrativo em furos.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    perfil = PerfilPlataforma.objects.filter(
        user=request.user,
        ativo=True,
        tipo_acesso__in=ADMIN_TIPOS_ACESSO_EMPRESA,
    ).select_related("empresa").first()
    if perfil:
        logger.info(
            "Contexto administrativo resolvido via PerfilPlataforma em furos.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em furos.py. user_id=%s",
        request.user.id,
    )
    return None



def _obter_empresa_admin_furos(request):
    contexto_admin = _obter_contexto_admin_furos(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or not empresa:
        logger.warning(
            "Contexto administrativo sem empresa em furos.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, None



def _obter_empregado_autenticado_furos(request):
    logger.debug(
        "A resolver empregado autenticado em furos.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
    if not empregado:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em furos.py. user_id=%s",
            request.user.id,
        )
        messages.error(
            request,
            "A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        )
        return None, redirect("projetos:redirect_after_login")

    if not empregado.empresa_id:
        logger.warning(
            "Empregado sem empresa associada em furos.py. user_id=%s, empregado_id=%s",
            request.user.id,
            empregado.id,
        )
        messages.error(request, "A tua conta não está associada a uma empresa. Contacta o administrador.")
        return None, redirect("projetos:redirect_after_login")

    return empregado, None



# ---------------- FUROS ----------------
@login_required
@empregado_required
def furo_detail_empregado(request, pk):
    logger.info(
        "Entrada na view furo_detail_empregado. user_id=%s, username='%s', furo_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_furos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_detail_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furo = get_object_or_404(Furo, pk=pk, empresa_id=empregado.empresa_id)

    trabalhou_no_furo = empregado.registos_diarios.filter(
        furo=furo,
        empresa_id=empregado.empresa_id,
    ).exists()
    if not trabalhou_no_furo:
        logger.warning(
            "Empregado sem permissão para furo_detail_empregado em furos.py. user_id=%s, empregado_id=%s, furo_id=%s",
            request.user.id,
            empregado.id,
            furo.id,
        )
        messages.error(request, "Não tens permissão para ver os detalhes deste furo.")
        return redirect("projetos:area_empregado")

    registos_furo = (
        RegistoDiarioEmpregado.objects
        .filter(furo=furo, empresa_id=empregado.empresa_id)
        .select_related("empregado", "projeto", "furo")
        .order_by("-data", "-criado_em")
    )

    medicoes_furo = (
        Medicao.objects
        .filter(furo=furo, empresa_id=empregado.empresa_id)
        .order_by("-criado_em", "-profundidade_medida")
    )

    logger.info(
        "View furo_detail_empregado carregada com sucesso em furos.py. user_id=%s, empregado_id=%s, furo_id=%s",
        request.user.id,
        empregado.id,
        furo.id,
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
    logger.info(
        "Entrada na view furo_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_create. user_id=%s", request.user.id)
        return resposta_erro

    if request.method == "POST":
        form = FuroCreateForm(request.POST, empresa=empresa_id)
        if form.is_valid():
            furo = criar_furo(form, empresa=empresa_id)
            logger.info(
                "Furo criado com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
                request.user.id,
                empresa.id,
                furo.pk,
            )
            messages.success(request, "Furo criado com sucesso.")
            return redirect(reverse("projetos:furo_detail", kwargs={"pk": furo.pk}))

        logger.warning(
            "Erro ao criar furo. user_id=%s, erros=%s",
            request.user.id,
            form.errors,
        )
        messages.error(request, "Erro ao criar o furo. Verifique os dados.")
    else:
        form = FuroCreateForm(empresa=empresa_id)

    return render(request, "projetos/form.html", {
        "form": form,
        "titulo": "Criar Novo Furo",
    })


@login_required
@admin_required
def furo_detail(request, pk):
    logger.info(
        "Entrada na view furo_detail. user_id=%s, username='%s', furo_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_detail. user_id=%s", request.user.id)
        return resposta_erro

    context = obter_contexto_detalhe_furo(pk, empresa=empresa_id)
    furo = context["furo"]
    context["configuracoes"] = obter_equipa_e_configuracao_por_furo(
        furo,
        empresa=empresa_id,
    )
    context["logs_geologicos_recentes"] = (
        LogGeologicoFuro.objects.filter(furo=furo, empresa_id=empresa_id)
        .select_related("missao_drone", "medicao")
        .order_by("-data_registo", "-criado_em")[:5]
    )
    context["missoes_drone_recentes"] = (
        MissaoDroneFuro.objects.filter(furo=furo, empresa_id=empresa_id)
        .order_by("-data_voo", "-criado_em")[:3]
    )

    logger.info(
        "View furo_detail carregada com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
        request.user.id,
        empresa.id,
        furo.pk,
    )
    return render(request, "projetos/furo_detail.html", context)

# Multiempresa: o administrador só pode listar e gerir furos da sua própria empresa.
@login_required
@admin_required
def furo_list(request):
    logger.info(
        "Entrada na view furo_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_list. user_id=%s", request.user.id)
        return resposta_erro

    furos = obter_lista_furos(empresa=empresa_id)
    logger.info(
        "View furo_list carregada com sucesso. user_id=%s, empresa_id=%s, total_furos=%s",
        request.user.id,
        empresa.id,
        furos.count() if hasattr(furos, "count") else "n/a",
    )
    return render(request, "projetos/furo_list.html", {"furos": furos})




@login_required
@admin_required
def furo_update(request, pk):
    logger.info(
        "Entrada na view furo_update. user_id=%s, username='%s', furo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_update. user_id=%s", request.user.id)
        return resposta_erro

    furo = get_object_or_404(Furo, pk=pk, empresa_id=empresa_id)

    if request.method == "POST":
        form = FuroForm(request.POST, instance=furo, empresa=empresa_id)
        if form.is_valid():
            furo = form.save(commit=False)
            furo.empresa_id = empresa_id

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

            logger.info(
                "Furo atualizado com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
                request.user.id,
                empresa.id,
                furo.pk,
            )
            messages.success(request, "Furo atualizado com sucesso.")
            return redirect(reverse("projetos:furo_detail", kwargs={"pk": furo.pk}))

        logger.warning(
            "Erro ao atualizar furo. user_id=%s, furo_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar o furo. Verifique os dados.")
    else:
        form = FuroForm(instance=furo, empresa=empresa_id)

    return render(request, "projetos/furo_update.html", {
        "form": form,
        "furo": furo,
    })



@login_required
@admin_required
def furo_delete(request, pk):
    logger.info(
        "Entrada na view furo_delete. user_id=%s, username='%s', furo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_delete. user_id=%s", request.user.id)
        return resposta_erro

    furo = get_object_or_404(Furo, pk=pk, empresa_id=empresa_id)
    if request.method == "POST":
        furo_id = furo.pk
        furo.delete()
        logger.info(
            "Furo apagado com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
            request.user.id,
            empresa.id,
            furo_id,
        )
        messages.success(request, "Furo apagado com sucesso.")
        return redirect(reverse("projetos:furo_list"))

    return render(request, "projetos/furo_confirm_delete.html", {"furo": furo})



@login_required
def furo_3d_geologico(request, furo_id):
    logger.info(
        "Entrada na view furo_3d_geologico. user_id=%s, username='%s', furo_id=%s",
        request.user.id,
        request.user.username,
        furo_id,
    )
    furo = None

    contexto_admin = _obter_contexto_admin_furos(request)
    if contexto_admin:
        empresa = getattr(contexto_admin, "empresa", None)
        empresa_id = getattr(contexto_admin, "empresa_id", None)

        if not empresa_id or not empresa:
            logger.warning(
                "Contexto administrativo sem empresa em furo_3d_geologico. user_id=%s",
                request.user.id,
            )
            messages.error(request, "O utilizador administrador não está associado a uma empresa.")
            return redirect("projetos:dashboard")

        furo = obter_furo(furo_id, empresa=empresa_id)
    else:
        empregado, resposta_erro = _obter_empregado_autenticado_furos(request)
        if resposta_erro:
            logger.warning("Acesso bloqueado na view furo_3d_geologico. user_id=%s", request.user.id)
            return resposta_erro

        furo = obter_furo(furo_id, empresa=empregado.empresa_id)

        trabalhou_no_furo = RegistoDiarioEmpregado.objects.filter(
            empregado=empregado,
            furo=furo,
            empresa_id=empregado.empresa_id,
        ).exists()

        if not trabalhou_no_furo:
            logger.warning(
                "Empregado sem permissão para furo_3d_geologico. user_id=%s, empregado_id=%s, furo_id=%s",
                request.user.id,
                empregado.id,
                furo.id,
            )
            messages.error(request, "Não tens permissão para ver o 3D deste furo.")
            return redirect("projetos:area_empregado")

    medicoes = list(
        furo.medicoes.filter(empresa_id=furo.empresa_id).order_by("profundidade_medida")
    )

    if not medicoes:
        logger.info(
            "Furo sem medições em furo_3d_geologico. user_id=%s, furo_id=%s",
            request.user.id,
            furo.id,
        )
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

    logger.info(
        "View furo_3d_geologico carregada com sucesso. user_id=%s, furo_id=%s, numero_medicoes=%s, estado_max=%s",
        request.user.id,
        furo.id,
        len(medicoes),
        estado_max,
    )
    return render(request, "projetos/furo_3d.html", {
        "furo": furo,
        "graph": graph,
        "numero_medicoes": len(medicoes),
        "profundidade_final": profundidade_final or 0.0,
        "dogleg_max": dogleg_max,
        "estado_max": estado_max,
    })
