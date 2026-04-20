import logging
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
from ..models.empregado import Empregados
from ..models.projeto import Projeto
from plataforma.models import PerfilPlataforma

logger = logging.getLogger("core")


ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


def _obter_contexto_admin_projetos(request):
    logger.debug(
        "A resolver contexto administrativo em projetos.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    admin_empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
    if admin_empregado:
        logger.info(
            "Contexto administrativo resolvido via Empregados em projetos.py. user_id=%s, empresa_id=%s",
            request.user.id,
            admin_empregado.empresa_id,
        )
        return admin_empregado

    perfil = PerfilPlataforma.objects.filter(
        user=request.user,
        ativo=True,
        tipo_acesso__in=ADMIN_TIPOS_ACESSO_EMPRESA,
    ).select_related("empresa").first()
    if perfil:
        logger.info(
            "Contexto administrativo resolvido via PerfilPlataforma em projetos.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em projetos.py. user_id=%s",
        request.user.id,
    )
    return None


def _obter_empresa_admin_projetos(request):
    contexto_admin = _obter_contexto_admin_projetos(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or empresa is None:
        logger.warning(
            "Contexto administrativo sem empresa válida em projetos.py. user_id=%s, empresa_id=%s, empresa_valor=%r",
            request.user.id,
            empresa_id,
            empresa,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa válida.")
        return None, redirect("projetos:dashboard")

    return empresa, None


# ----------------- Globo ------------------------------ #
@login_required
@admin_required
def globo_projetos(request):
    logger.info(
        "Entrada na view globo_projetos. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view globo_projetos. user_id=%s", request.user.id)
        return resposta_erro

    projetos = Projeto.objects.filter(
        empresa_id=empresa_id,
    ).exclude(
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

    logger.info(
        "View globo_projetos carregada com sucesso. user_id=%s, empresa_id=%s, total_projetos=%s",
        request.user.id,
        empresa.id,
        projetos.count(),
    )
    return render(request, "projetos/globo.html", {"graph": graph})


# Multiempresa: o administrador só pode listar e gerir projetos da sua própria empresa.
@login_required
@admin_required
def projeto_list(request):
    logger.info(
        "Entrada na view projeto_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_list. user_id=%s", request.user.id)
        return resposta_erro

    logger.debug(
        "Empresa resolvida em projeto_list. user_id=%s, empresa_tipo=%s, empresa_id=%s, empresa_repr=%r",
        request.user.id,
        empresa.__class__.__name__ if empresa else None,
        getattr(empresa, "pk", None),
        empresa,
    )

    projetos_qs = obter_lista_projetos(empresa=empresa)
    projetos_serializaveis = list(projetos_qs.values(
        "id", "pk", "nome", "cliente", "cidade", "pais", "localizacao_lat", "localizacao_lon"
    ))

    context = {"projetos": projetos_serializaveis}
    return render(request, "projetos/projeto_list.html", context)


@login_required
@admin_required
def projeto_update(request, pk):
    logger.info(
        "Entrada na view projeto_update. user_id=%s, username='%s', projeto_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_update. user_id=%s", request.user.id)
        return resposta_erro

    projeto = get_object_or_404(Projeto, pk=pk, empresa_id=empresa_id)
    form = ProjetoForm(request.POST or None, instance=projeto, empresa=empresa_id)

    if request.method == "POST":
        if form.is_valid():
            projeto = atualizar_projeto(form, empresa=empresa_id)
            logger.info(
                "Projeto atualizado com sucesso. user_id=%s, empresa_id=%s, projeto_id=%s",
                request.user.id,
                empresa.id,
                projeto.pk,
            )
            messages.success(request, "Projeto atualizado com sucesso.")
            return redirect("projetos:projeto_detail", pk=projeto.pk)

        logger.warning(
            "Erro ao atualizar projeto. user_id=%s, projeto_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar o projeto. Verifique os dados.")

    return render(request, "projetos/projeto_editar.html", {
        "form": form,
        "projeto": projeto,
    })


@login_required
@admin_required
def projeto_create(request):
    logger.info(
        "Entrada na view projeto_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_create. user_id=%s", request.user.id)
        return resposta_erro

    if request.method == "POST":
        form = ProjetoForm(request.POST, empresa=empresa_id)
        if form.is_valid():
            projeto = criar_projeto(form, empresa=empresa_id)
            logger.info(
                "Projeto criado com sucesso. user_id=%s, empresa_id=%s, projeto_id=%s",
                request.user.id,
                empresa.id,
                getattr(projeto, "pk", None),
            )
            messages.success(request, "Projeto criado com sucesso.")
            return redirect("projetos:projeto_list")

        logger.warning(
            "Erro ao criar projeto. user_id=%s, erros=%s",
            request.user.id,
            form.errors,
        )
        messages.error(request, "Erro ao criar o projeto. Verifique os dados.")
    else:
        form = ProjetoForm(empresa=empresa_id)

    return render(request, "projetos/projeto_form.html", {"form": form})


@login_required
@admin_required
def projeto_delete(request, pk):
    logger.info(
        "Entrada na view projeto_delete. user_id=%s, username='%s', projeto_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_delete. user_id=%s", request.user.id)
        return resposta_erro

    projeto = get_object_or_404(Projeto, pk=pk, empresa_id=empresa_id)

    if request.method == "POST":
        projeto_id = projeto.pk
        projeto.delete()
        logger.info(
            "Projeto apagado com sucesso. user_id=%s, empresa_id=%s, projeto_id=%s",
            request.user.id,
            empresa.id,
            projeto_id,
        )
        messages.success(request, "Projeto apagado com sucesso.")
        return redirect("projetos:projeto_list")

    return render(request, "projetos/projeto_confirm_delete.html", {
        "projeto": projeto,
    })


@login_required
@admin_required
def projeto_detail(request, pk):
    logger.info(
        "Entrada na view projeto_detail. user_id=%s, username='%s', projeto_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_detail. user_id=%s", request.user.id)
        return resposta_erro

    context = obter_contexto_projeto_detail(pk, empresa=empresa)
    logger.info(
        "View projeto_detail carregada com sucesso. user_id=%s, empresa_id=%s, projeto_pk=%s",
        request.user.id,
        empresa.id,
        pk,
    )
    return render(request, "projetos/projeto_detail.html", context)


# ---------------- 3D ----------------
@login_required
@admin_required
def projeto_3d(request, pk):
    logger.info(
        "Entrada na view projeto_3d. user_id=%s, username='%s', projeto_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_3d. user_id=%s", request.user.id)
        return resposta_erro

    projeto = obter_projeto(pk, empresa=empresa)
    furos = obter_furos_projeto(projeto, empresa=empresa)
    furos_3d = obter_dados_3d_projeto(projeto, empresa=empresa)

    fig = go.Figure()

    for furo in furos:
        medicoes = list(
            furo.medicoes.filter(empresa_id=empresa_id).order_by("profundidade_medida")
        )

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

    logger.info(
        "View projeto_3d carregada com sucesso. user_id=%s, empresa_id=%s, projeto_id=%s, total_furos=%s",
        request.user.id,
        empresa.id,
        getattr(projeto, "pk", None),
        len(furos),
    )
    return render(request, "projetos/projeto_3d.html", context)