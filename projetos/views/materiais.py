import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.permissions import admin_required
from ..decorators import empregado_required

from ..forms.material import (
    MaterialForm,
    EntradaMaterialForm,
    SaidaMaterialForm,
    LevantamentoMaterialForm,
    DevolucaoMaterialForm,
)

from projetos.selectors.material import (
    obter_contexto_filtros_levantamentos_admin,
    obter_lista_materiais_filtrada_nome,
    obter_material_por_id_empresa,
    obter_contexto_material_detail,
    obter_levantamentos_empregado,
    obter_devolucoes_empregado,
    obter_levantamentos_admin_filtrados,
    obter_devolucoes_admin,
)
from projetos.services.acesso_contexto import (
    obter_empregado_autenticado_contexto,
    obter_empresa_admin_contexto,
)
from projetos.selectors.acesso import obter_perfil_ativo_por_user

from projetos.services.stock import (
    apagar_material_admin,
    processar_fluxo_movimento_material_form,
    processar_devolucao_material_form,
    processar_fluxo_entrada_saida_material_admin,
    processar_fluxo_material_admin_form,
    processar_levantamento_material_form,
)

logger = logging.getLogger("core")


# ---------------- HELPERS ----------------
def _obter_empresa_admin_materiais(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        logger.warning(
            "Falha ao resolver empresa administrativa em materiais.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empresa, None



def _obter_empregado_autenticado_materiais(request):
    logger.debug(
        "A resolver empregado autenticado em materiais.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado, ligado_por_fallback, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
    )
    if resposta_erro:
        logger.warning(
            "Utilizador sem contexto de empregado em materiais.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro

    if ligado_por_fallback:
        logger.warning(
            "Ligação automática User -> Empregados executada em materiais.py. user_id=%s, empregado_id=%s, empresa_id=%s, email='%s'",
            request.user.id,
            empregado.id,
            empregado.empresa_id,
            getattr(request.user, "email", ""),
        )
    return empregado, None


def _conta_individual(user):
    perfil = obter_perfil_ativo_por_user(user)
    return bool(perfil and perfil.tipo_acesso == "individual")


def _render_material_form(request, form, titulo, material=None):
    context = {
        "form": form,
        "titulo": titulo,
    }
    if material is not None:
        context["material"] = material
    return render(request, "projetos/material_form.html", context)


def _processar_movimento_material(
    *,
    request,
    empregado,
    form_class,
    processar_fn,
    sucesso_msg,
    erro_msg,
    redirect_name,
    template_name,
    titulo,
    log_sucesso,
    log_erro,
):
    fluxo = processar_fluxo_movimento_material_form(
        method=request.method,
        post_data=request.POST,
        material_id=request.GET.get("material"),
        empregado=empregado,
        form_class=form_class,
        processar_fn=processar_fn,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            movimento = resultado["movimento"]
            logger.info(
                log_sucesso,
                request.user.id,
                empregado.id,
                empregado.empresa_id,
                movimento.id,
                movimento.material_id,
                movimento.quantidade,
            )
            messages.success(request, sucesso_msg)
            return redirect(redirect_name)
        if resultado["erro"] == "form_invalido":
            logger.warning(log_erro, request.user.id, empregado.id, resultado.get("erros_form"))
            messages.error(request, erro_msg)

    return render(request, template_name, {
        "form": form,
        "empregado": empregado,
        "titulo": titulo,
    })

@login_required
@admin_required
def entrada_material_view(request, material_id):
    logger.info(
        "Entrada na view entrada_material_view. user_id=%s, username='%s', material_id=%s, method=%s",
        request.user.id,
        request.user.username,
        material_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view entrada_material_view. user_id=%s", request.user.id)
        return resposta_erro

    material = obter_material_por_id_empresa(material_id, empresa)

    fluxo = processar_fluxo_entrada_saida_material_admin(
        method=request.method,
        post_data=request.POST,
        form_class=EntradaMaterialForm,
        material=material,
        empresa=empresa,
        tipo="entrada",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            logger.info(
                "Entrada de material registada com sucesso. user_id=%s, empresa_id=%s, material_id=%s",
                request.user.id,
                empresa.id,
                material.id,
            )
            messages.success(request, "Entrada de material registada com sucesso.")
            return redirect("projetos:material_list")
        if resultado["erro"] == "validacao":
            logger.warning(
                "Erro de validação em entrada_material_view. user_id=%s, material_id=%s",
                request.user.id,
                material.id,
            )

    context = {
        "material": material,
        "form": form,
    }

    return render(request, "projetos/entrada_material.html", context)

@login_required
@admin_required
def saida_material_view(request, material_id):
    logger.info(
        "Entrada na view saida_material_view. user_id=%s, username='%s', material_id=%s, method=%s",
        request.user.id,
        request.user.username,
        material_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view saida_material_view. user_id=%s", request.user.id)
        return resposta_erro

    material = obter_material_por_id_empresa(material_id, empresa)

    fluxo = processar_fluxo_entrada_saida_material_admin(
        method=request.method,
        post_data=request.POST,
        form_class=SaidaMaterialForm,
        material=material,
        empresa=empresa,
        tipo="saida",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            logger.info(
                "Saída de material registada com sucesso. user_id=%s, empresa_id=%s, material_id=%s",
                request.user.id,
                empresa.id,
                material.id,
            )
            messages.success(request, "Saída de material registada com sucesso.")
            return redirect("projetos:material_list")
        if resultado["erro"] == "validacao":
            logger.warning(
                "Erro de validação em saida_material_view. user_id=%s, material_id=%s",
                request.user.id,
                material.id,
            )

    context = {
        "material": material,
        "form": form,
    }

    return render(request, "projetos/saida_material.html", context)

# Multiempresa: o administrador só pode listar e gerir materiais da sua própria empresa.
@login_required
@admin_required
def material_list(request):
    logger.info(
        "Entrada na view material_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view material_list. user_id=%s", request.user.id)
        return resposta_erro

    nome = (request.GET.get("nome") or "").strip()
    materiais = obter_lista_materiais_filtrada_nome(empresa=empresa, nome=nome)

    logger.info(
        "View material_list carregada com sucesso. user_id=%s, empresa_id=%s, total_materiais=%s, filtro_nome='%s'",
        request.user.id,
        empresa.id,
        materiais.count() if hasattr(materiais, "count") else "n/a",
        nome,
    )
    return render(request, 'projetos/material_list.html', {
        'materiais': materiais,
        'filtros': {
            'nome': nome,
        }
    })


@login_required
@admin_required
def material_detail(request, material_id):
    logger.info(
        "Entrada na view material_detail. user_id=%s, username='%s', material_id=%s",
        request.user.id,
        request.user.username,
        material_id,
    )
    empresa, resposta_erro = _obter_empresa_admin_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view material_detail. user_id=%s", request.user.id)
        return resposta_erro

    context = obter_contexto_material_detail(material_id, empresa=empresa)
    logger.info(
        "View material_detail carregada com sucesso. user_id=%s, empresa_id=%s, material_id=%s",
        request.user.id,
        empresa.id,
        material_id,
    )
    return render(request, 'projetos/material_detail.html', context)


@login_required
@admin_required
def material_create(request):
    logger.info(
        "Entrada na view material_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view material_create. user_id=%s", request.user.id)
        return resposta_erro

    fluxo = processar_fluxo_material_admin_form(
        method=request.method,
        post_data=request.POST,
        form_class=MaterialForm,
        empresa=empresa,
        acao="create",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            material = resultado["material"]
            logger.info(
                "Material criado com sucesso. user_id=%s, empresa_id=%s, material_id=%s",
                request.user.id,
                empresa.id,
                material.id,
            )
            messages.success(request, "Material criado com sucesso.")
            return redirect("projetos:material_detail", material_id=material.id)
        logger.warning("Erro ao criar material. user_id=%s, erros=%s", request.user.id, resultado.get("erros_form"))
        messages.error(request, "Erro ao criar o material. Verifique os dados.")

    return _render_material_form(request, form, "Novo Material")


@login_required
@empregado_required
def material_create_empregado(request):
    logger.info(
        "Entrada na view material_create_empregado. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    if not _conta_individual(request.user):
        messages.error(
            request,
            "Criação de materiais nesta área está disponível apenas para contas individuais.",
        )
        return redirect("projetos:materiais_disponiveis_empregado")

    empregado, resposta_erro = _obter_empregado_autenticado_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view material_create_empregado. user_id=%s", request.user.id)
        return resposta_erro

    fluxo = processar_fluxo_material_admin_form(
        method=request.method,
        post_data=request.POST,
        form_class=MaterialForm,
        empresa=empregado.empresa,
        acao="create",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            material = resultado["material"]
            logger.info(
                "Material criado por conta individual. user_id=%s, empregado_id=%s, empresa_id=%s, material_id=%s",
                request.user.id,
                empregado.id,
                empregado.empresa_id,
                material.id,
            )
            messages.success(request, "Material criado com sucesso.")
            return redirect("projetos:materiais_disponiveis_empregado")
        logger.warning(
            "Erro ao criar material por conta individual. user_id=%s, erros=%s",
            request.user.id,
            resultado.get("erros_form"),
        )
        messages.error(request, "Erro ao criar o material. Verifique os dados.")

    return _render_material_form(request, form, "Novo Material")


@login_required
@admin_required
def material_update(request, material_id):
    logger.info(
        "Entrada na view material_update. user_id=%s, username='%s', material_id=%s, method=%s",
        request.user.id,
        request.user.username,
        material_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view material_update. user_id=%s", request.user.id)
        return resposta_erro

    material = obter_material_por_id_empresa(material_id, empresa)

    fluxo = processar_fluxo_material_admin_form(
        method=request.method,
        post_data=request.POST,
        form_class=MaterialForm,
        empresa=empresa,
        acao="update",
        instance=material,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            material_atualizado = resultado["material"]
            logger.info(
                "Material atualizado com sucesso. user_id=%s, empresa_id=%s, material_id=%s",
                request.user.id,
                empresa.id,
                material_atualizado.id,
            )
            messages.success(request, "Material atualizado com sucesso.")
            return redirect("projetos:material_detail", material_id=material_atualizado.id)
        logger.warning("Erro ao atualizar material. user_id=%s, erros=%s", request.user.id, resultado.get("erros_form"))
        messages.error(request, "Erro ao atualizar o material. Verifique os dados.")

    return _render_material_form(request, form, "Editar Material", material=material)


@login_required
@admin_required
def material_delete(request, material_id):
    logger.info(
        "Entrada na view material_delete. user_id=%s, username='%s', material_id=%s, method=%s",
        request.user.id,
        request.user.username,
        material_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view material_delete. user_id=%s", request.user.id)
        return resposta_erro

    material = obter_material_por_id_empresa(material_id, empresa)

    if request.method == "POST":
        material_id_removido = apagar_material_admin(material=material, empresa=empresa)
        logger.info(
            "Material apagado com sucesso. user_id=%s, empresa_id=%s, material_id=%s",
            request.user.id,
            empresa.id,
            material_id_removido,
        )
        messages.success(request, "Material apagado com sucesso.")
        return redirect("projetos:material_list")

    return render(request, 'projetos/material_confirm_delete.html', {
        'material': material
    })

# ------------ Levantamento Materiais ----------------- #
@login_required
@empregado_required
def levantamento_material_create(request):
    logger.info(
        "Entrada na view levantamento_material_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view levantamento_material_create. user_id=%s", request.user.id)
        return resposta_erro

    return _processar_movimento_material(
        request=request,
        empregado=empregado,
        form_class=LevantamentoMaterialForm,
        processar_fn=processar_levantamento_material_form,
        sucesso_msg="Levantamento registado com sucesso.",
        erro_msg="Erro ao registar levantamento.",
        redirect_name="projetos:levantamento_list",
        template_name="projetos/levantamento_material_form.html",
        titulo="Novo Levantamento de Material",
        log_sucesso="Levantamento registado com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s, levantamento_id=%s, material_id=%s, quantidade=%s",
        log_erro="Erro ao registar levantamento. user_id=%s, empregado_id=%s, erros=%s",
    )


@login_required
@empregado_required
def levantamento_material_list(request):
    logger.info(
        "Entrada na view levantamento_material_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view levantamento_material_list. user_id=%s", request.user.id)
        return resposta_erro

    levantamentos = obter_levantamentos_empregado(empregado)
    logger.info(
        "View levantamento_material_list carregada com sucesso. user_id=%s, empregado_id=%s, total_levantamentos=%s",
        request.user.id,
        empregado.id,
        levantamentos.count() if hasattr(levantamentos, "count") else "n/a",
    )

    return render(request, "projetos/levantamento_material_list.html", {
        "levantamentos": levantamentos
    })

@login_required
@admin_required
def levantamento_material_admin_list(request):
    logger.info(
        "Entrada na view levantamento_material_admin_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view levantamento_material_admin_list. user_id=%s", request.user.id)
        return resposta_erro
    resultados = obter_levantamentos_admin_filtrados(
        empresa=empresa,
        filtros=request.GET,
    )
    levantamentos = resultados["levantamentos"]
    contexto_filtros = obter_contexto_filtros_levantamentos_admin(empresa=empresa)

    logger.info(
        "View levantamento_material_admin_list carregada com sucesso. user_id=%s, empresa_id=%s, total_levantamentos=%s",
        request.user.id,
        empresa.id,
        levantamentos.count() if hasattr(levantamentos, "count") else "n/a",
    )
    return render(request, "projetos/levantamento_material_admin_list.html", {
        "levantamentos": levantamentos,
        "empregados": contexto_filtros["empregados"],
        "materiais": contexto_filtros["materiais"],
        "projetos": contexto_filtros["projetos"],
        "filtros": resultados["filtros"],
    })

# ----------- Devolução MAteriais -----------------------#
@login_required
@empregado_required
def devolucao_material_create(request):
    logger.info(
        "Entrada na view devolucao_material_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view devolucao_material_create. user_id=%s", request.user.id)
        return resposta_erro

    return _processar_movimento_material(
        request=request,
        empregado=empregado,
        form_class=DevolucaoMaterialForm,
        processar_fn=processar_devolucao_material_form,
        sucesso_msg="Devolução registada com sucesso.",
        erro_msg="Erro ao registar devolução.",
        redirect_name="projetos:devolucao_material_list",
        template_name="projetos/devolucao_material_form.html",
        titulo="Nova Devolução de Material",
        log_sucesso="Devolução registada com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s, devolucao_id=%s, material_id=%s, quantidade=%s",
        log_erro="Erro ao registar devolução. user_id=%s, empregado_id=%s, erros=%s",
    )


@login_required
@empregado_required
def devolucao_material_list(request):
    logger.info(
        "Entrada na view devolucao_material_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view devolucao_material_list. user_id=%s", request.user.id)
        return resposta_erro

    devolucoes = obter_devolucoes_empregado(empregado)
    logger.info(
        "View devolucao_material_list carregada com sucesso. user_id=%s, empregado_id=%s, total_devolucoes=%s",
        request.user.id,
        empregado.id,
        devolucoes.count() if hasattr(devolucoes, "count") else "n/a",
    )

    return render(request, "projetos/devolucao_material_list.html", {
        "devolucoes": devolucoes
    })

@login_required
@admin_required
def devolucao_material_admin_list(request):
    logger.info(
        "Entrada na view devolucao_material_admin_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_materiais(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view devolucao_material_admin_list. user_id=%s", request.user.id)
        return resposta_erro

    devolucoes = obter_devolucoes_admin(empresa=empresa)
    logger.info(
        "View devolucao_material_admin_list carregada com sucesso. user_id=%s, empresa_id=%s, total_devolucoes=%s",
        request.user.id,
        empresa.id,
        devolucoes.count() if hasattr(devolucoes, "count") else "n/a",
    )

    return render(request, "projetos/devolucao_material_admin_list.html", {
        "devolucoes": devolucoes
    })
