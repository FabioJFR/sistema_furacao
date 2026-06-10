import logging
import math

import plotly.graph_objects as go
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.permissions import admin_required, user_is_global_admin

from projetos.selectors.dashboard import obter_empresas_contexto_dashboard
from projetos.selectors.projetos import (
    obter_contexto_projeto_detail,
    obter_dados_3d_projeto,
    obter_furos_projeto,
    obter_ligacao_empregado_projeto,
    obter_lista_projetos_serializaveis,
    obter_projeto,
    obter_projetos_globo,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.projetos import (
    apagar_projeto,
    processar_acao_associar_empregado_projeto,
    processar_fluxo_form_projeto,
    atualizar_projeto,
    criar_projeto,
)
from projetos.services.empregados import terminar_ligacao_projeto_empregado
from projetos.utils.tragetoria import calcular_trajetoria_min_curv

from ..forms.empregado import ProjetoEmpregadoForm
from ..forms.projeto import ProjetoForm
logger = logging.getLogger("core")


def _obter_empresa_admin_projetos(request, *, exigir_empresa_global=False):
    if exigir_empresa_global and user_is_global_admin(request.user):
        empresa_id = request.GET.get("empresa") or request.GET.get("empresa_contexto")
        if not empresa_id:
            messages.info(request, "Seleciona explicitamente a empresa do projeto para continuar.")
            return None, redirect("projetos:projeto_list")

    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa válida.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        logger.warning(
            "Falha ao resolver empresa administrativa em projetos.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empresa, None


def _empresa_id(empresa):
    return getattr(empresa, "pk", empresa) if empresa is not None else None


def _url_projeto_contexto(*, request, projeto, empresa):
    url = projeto.get_absolute_url()
    if user_is_global_admin(request.user):
        return f"{url}?empresa_contexto={empresa.pk}"
    return url


def _query_empresa_contexto(*, request, empresa):
    if user_is_global_admin(request.user):
        return f"?empresa_contexto={empresa.pk}"
    return ""


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

    projetos = obter_projetos_globo(empresa=empresa_id)

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

    visao_global = user_is_global_admin(request.user)
    if visao_global:
        context = {
            "projetos": obter_lista_projetos_serializaveis(),
            "visao_global": True,
            "empresas_contexto": obter_empresas_contexto_dashboard(),
        }
        return render(request, "projetos/projeto_list.html", context)

    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_list. user_id=%s", request.user.id)
        return resposta_erro

    context = {"projetos": obter_lista_projetos_serializaveis(empresa=empresa), "visao_global": False}
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
    empresa, resposta_erro = _obter_empresa_admin_projetos(request, exigir_empresa_global=True)
    empresa_id = _empresa_id(empresa)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_update. user_id=%s", request.user.id)
        return resposta_erro

    projeto = obter_projeto(pk, empresa=empresa_id)
    fluxo = processar_fluxo_form_projeto(
        method=request.method,
        post_data=request.POST,
        form_class=ProjetoForm,
        empresa=empresa,
        on_success=atualizar_projeto,
        sucesso_msg="Projeto atualizado com sucesso.",
        erro_msg="Erro ao atualizar o projeto. Verifique os dados.",
        instance=projeto,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["ok"]:
            projeto = resultado["projeto"]
            logger.info(
                "Projeto atualizado com sucesso. user_id=%s, empresa_id=%s, projeto_id=%s",
                request.user.id,
                empresa.id,
                getattr(projeto, "pk", None),
            )
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect(_url_projeto_contexto(request=request, projeto=projeto, empresa=empresa))
        logger.warning(
            "Erro ao atualizar projeto. user_id=%s, erros=%s",
            request.user.id,
            resultado["erros"],
        )
        messages.error(request, resultado["mensagem_erro"])

    return render(request, "projetos/projeto_editar.html", {
        "form": form,
        "projeto": projeto,
        "empresa_contexto_query": _query_empresa_contexto(request=request, empresa=empresa),
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
    empresa, resposta_erro = _obter_empresa_admin_projetos(request, exigir_empresa_global=True)
    empresa_id = _empresa_id(empresa)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_create. user_id=%s", request.user.id)
        return resposta_erro

    fluxo = processar_fluxo_form_projeto(
        method=request.method,
        post_data=request.POST,
        form_class=ProjetoForm,
        empresa=empresa,
        on_success=criar_projeto,
        sucesso_msg="Projeto criado com sucesso.",
        erro_msg="Erro ao criar o projeto. Verifique os dados.",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["ok"]:
            projeto = resultado["projeto"]
            logger.info(
                "Projeto criado com sucesso. user_id=%s, empresa_id=%s, projeto_id=%s",
                request.user.id,
                empresa.id,
                getattr(projeto, "pk", None),
            )
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect("projetos:projeto_list")
        logger.warning(
            "Erro ao criar projeto. user_id=%s, erros=%s",
            request.user.id,
            resultado["erros"],
        )
        messages.error(request, resultado["mensagem_erro"])

    return render(request, "projetos/projeto_form.html", {
        "form": form,
        "empresa_contexto_query": _query_empresa_contexto(request=request, empresa=empresa),
        "empresa_contexto": empresa,
    })


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
    empresa, resposta_erro = _obter_empresa_admin_projetos(request, exigir_empresa_global=True)
    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_delete. user_id=%s", request.user.id)
        return resposta_erro

    projeto = obter_projeto(pk, empresa=empresa_id)

    if request.method == "POST":
        projeto_id = apagar_projeto(projeto=projeto, empresa=empresa_id)
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
        "empresa_contexto_query": _query_empresa_contexto(request=request, empresa=empresa),
    })


@login_required
@admin_required
def projeto_detail_legacy(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_projetos(request, exigir_empresa_global=True)
    if resposta_erro:
        return resposta_erro

    projeto = obter_projeto(pk, empresa=empresa)
    return redirect(_url_projeto_contexto(request=request, projeto=projeto, empresa=empresa))


@login_required
@admin_required
def projeto_detail(request, pk, slug):
    logger.info(
        "Entrada na view projeto_detail. user_id=%s, username='%s', projeto_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, resposta_erro = _obter_empresa_admin_projetos(request, exigir_empresa_global=True)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_detail. user_id=%s", request.user.id)
        return resposta_erro

    context = obter_contexto_projeto_detail(pk, empresa=empresa)
    projeto = context["projeto"]

    if slug != projeto.slug_url:
        return redirect(_url_projeto_contexto(request=request, projeto=projeto, empresa=empresa))

    context["trabalhador_form"] = ProjetoEmpregadoForm(empresa=empresa, projeto=context["projeto"])
    context["page_title"] = f"Projeto · {projeto.nome}"
    context["empresa_contexto_query"] = _query_empresa_contexto(request=request, empresa=empresa)
    logger.info(
        "View projeto_detail carregada com sucesso. user_id=%s, empresa_id=%s, projeto_pk=%s",
        request.user.id,
        empresa.id,
        pk,
    )
    return render(request, "projetos/projeto_detail.html", context)


@login_required
@admin_required
def projeto_adicionar_empregado(request, pk):
    logger.info(
        "Entrada na view projeto_adicionar_empregado. user_id=%s, username='%s', projeto_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_projetos(request, exigir_empresa_global=True)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_adicionar_empregado. user_id=%s", request.user.id)
        return resposta_erro

    projeto = obter_projeto(pk, empresa=empresa)
    if request.method != "POST":
        messages.error(request, "Método inválido para associar trabalhador ao projeto.")
        return redirect(_url_projeto_contexto(request=request, projeto=projeto, empresa=empresa))

    form = ProjetoEmpregadoForm(request.POST, empresa=empresa, projeto=projeto)
    resultado = processar_acao_associar_empregado_projeto(
        form=form,
        projeto=projeto,
        empresa=empresa,
    )
    if resultado["mensagem_sucesso"]:
        messages.success(request, resultado["mensagem_sucesso"])
    if resultado["mensagem_aviso"]:
        messages.warning(request, resultado["mensagem_aviso"])
    if resultado["mensagem_erro"]:
        messages.error(request, resultado["mensagem_erro"])

    return redirect(_url_projeto_contexto(request=request, projeto=projeto, empresa=empresa))


@login_required
@admin_required
def projeto_remover_empregado(request, pk, ligacao_id):
    logger.info(
        "Entrada na view projeto_remover_empregado. user_id=%s, username='%s', projeto_pk=%s, ligacao_id=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        ligacao_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_projetos(request, exigir_empresa_global=True)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_remover_empregado. user_id=%s", request.user.id)
        return resposta_erro

    projeto = obter_projeto(pk, empresa=empresa)
    ligacao = obter_ligacao_empregado_projeto(
        ligacao_id=ligacao_id,
        projeto=projeto,
        empresa=empresa,
    )

    if request.method == "POST":
        terminar_ligacao_projeto_empregado(ligacao, empresa=empresa)
        messages.success(request, f"{ligacao.empregado.nome} foi removido da equipa ativa do projeto.")
    else:
        messages.error(request, "Método inválido para remover trabalhador do projeto.")

    return redirect(_url_projeto_contexto(request=request, projeto=projeto, empresa=empresa))


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
    empresa, resposta_erro = _obter_empresa_admin_projetos(request, exigir_empresa_global=True)
    empresa_id = _empresa_id(empresa)
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
