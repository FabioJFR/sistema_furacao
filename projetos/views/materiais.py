import logging
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions import admin_required
from ..decorators import empregado_required

from ..models.material import Material
from ..forms.material import (
    MaterialForm,
    EntradaMaterialForm,
    SaidaMaterialForm,
    LevantamentoMaterialForm,
    DevolucaoMaterialForm,
)

from projetos.selectors.acesso import (
    obter_contexto_admin_projetos,
    resolver_empregado_por_user_ou_email,
)
from projetos.selectors.material import (
    obter_contexto_filtros_levantamentos_admin,
    obter_lista_materiais_filtrada_nome,
    obter_contexto_material_detail,
    obter_levantamentos_empregado,
    obter_devolucoes_empregado,
    obter_levantamentos_admin_filtrados,
    obter_devolucoes_admin,
)

from projetos.services.stock import (
    registrar_entrada_material,
    registrar_saida_material,
)

logger = logging.getLogger("core")


# ---------------- HELPERS ----------------
def _obter_contexto_admin_materiais(request):
    logger.debug(
        "A resolver contexto administrativo em materiais.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    perfil = obter_contexto_admin_projetos(request.user)
    if perfil:
        logger.info(
            "Contexto administrativo resolvido via PerfilPlataforma em materiais.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em materiais.py. user_id=%s",
        request.user.id,
    )
    return None



def _obter_empresa_admin_materiais(request):
    contexto_admin = _obter_contexto_admin_materiais(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or not empresa:
        logger.warning(
            "Contexto administrativo sem empresa em materiais.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, None



def _obter_empregado_autenticado_materiais(request):
    logger.debug(
        "A resolver empregado autenticado em materiais.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado = _resolver_empregado_por_user_ou_email(request.user)
    if not empregado:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em materiais.py. user_id=%s",
            request.user.id,
        )
        messages.error(
            request,
            "A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        )
        return None, redirect("projetos:redirect_after_login")

    if not empregado.empresa_id:
        logger.warning(
            "Empregado sem empresa associada em materiais.py. user_id=%s, empregado_id=%s",
            request.user.id,
            empregado.id,
        )
        messages.error(request, "A tua conta não está associada a uma empresa. Contacta o administrador.")
        return None, redirect("projetos:redirect_after_login")

    return empregado, None


def _resolver_empregado_por_user_ou_email(user):
    empregado, ligado_por_fallback = resolver_empregado_por_user_ou_email(user)
    if ligado_por_fallback and empregado is not None:
        logger.warning(
            "Ligação automática User -> Empregados executada em materiais.py. user_id=%s, empregado_id=%s, empresa_id=%s, email='%s'",
            user.id,
            empregado.id,
            empregado.empresa_id,
            getattr(user, "email", ""),
        )
    return empregado

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

    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    material = get_object_or_404(Material, id=material_id, empresa_id=empresa_id)

    if request.method == "POST":
        form = EntradaMaterialForm(request.POST)

        if form.is_valid():
            try:
                registrar_entrada_material(
                    material=material,
                    quantidade=form.cleaned_data["quantidade"],
                )
                logger.info(
                    "Entrada de material registada com sucesso. user_id=%s, empresa_id=%s, material_id=%s",
                    request.user.id,
                    empresa.id,
                    material.id,
                )
                messages.success(request, "Entrada de material registada com sucesso.")
                return redirect("projetos:material_list")

            except ValidationError as e:
                logger.warning(
                    "Erro de validação em entrada_material_view. user_id=%s, material_id=%s, erro=%s",
                    request.user.id,
                    material.id,
                    e,
                )
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

    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    material = get_object_or_404(Material, id=material_id, empresa_id=empresa_id)

    if request.method == "POST":
        form = SaidaMaterialForm(request.POST)

        if form.is_valid():
            try:
                registrar_saida_material(
                    material=material,
                    quantidade=form.cleaned_data["quantidade"],
                )
                logger.info(
                    "Saída de material registada com sucesso. user_id=%s, empresa_id=%s, material_id=%s",
                    request.user.id,
                    empresa.id,
                    material.id,
                )
                messages.success(request, "Saída de material registada com sucesso.")
                return redirect("projetos:material_list")

            except ValidationError as e:
                logger.warning(
                    "Erro de validação em saida_material_view. user_id=%s, material_id=%s, erro=%s",
                    request.user.id,
                    material.id,
                    e,
                )
                form.add_error(None, e)
    else:
        form = SaidaMaterialForm()

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

    if request.method == "POST":
        form = MaterialForm(request.POST, empresa=empresa)
        if form.is_valid():
            material = form.save(commit=False)
            material.empresa = empresa
            material.save()
            logger.info(
                "Material criado com sucesso. user_id=%s, empresa_id=%s, material_id=%s",
                request.user.id,
                empresa.id,
                material.id,
            )
            messages.success(request, "Material criado com sucesso.")
            return redirect("projetos:material_detail", material_id=material.id)
        else:
            logger.warning(
                "Erro ao criar material. user_id=%s, erros=%s",
                request.user.id,
                form.errors,
            )
            messages.error(request, "Erro ao criar o material. Verifique os dados.")
    else:
        form = MaterialForm(empresa=empresa)

    return render(request, 'projetos/material_form.html', {
        'form': form,
        'titulo': 'Novo Material'
    })


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

    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    material = get_object_or_404(Material, id=material_id, empresa_id=empresa_id)

    if request.method == "POST":
        form = MaterialForm(request.POST, instance=material, empresa=empresa)
        if form.is_valid():
            material = form.save(commit=False)
            material.empresa = empresa
            material.save()
            logger.info(
                "Material atualizado com sucesso. user_id=%s, empresa_id=%s, material_id=%s",
                request.user.id,
                empresa.id,
                material.id,
            )
            messages.success(request, "Material atualizado com sucesso.")
            return redirect("projetos:material_detail", material_id=material.id)
        else:
            logger.warning(
                "Erro ao atualizar material. user_id=%s, material_id=%s, erros=%s",
                request.user.id,
                material_id,
                form.errors,
            )
            messages.error(request, "Erro ao atualizar o material. Verifique os dados.")
    else:
        form = MaterialForm(instance=material, empresa=empresa)

    return render(request, 'projetos/material_form.html', {
        'form': form,
        'titulo': 'Editar Material',
        'material': material
    })


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

    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    material = get_object_or_404(Material, id=material_id, empresa_id=empresa_id)

    if request.method == "POST":
        material_id_removido = material.id
        material.delete()
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

    material_id = request.GET.get("material")
    material_selecionado = None

    if material_id:
        material_selecionado = get_object_or_404(
            Material,
            id=material_id,
            empresa_id=empregado.empresa_id,
        )

    if request.method == "POST":
        form = LevantamentoMaterialForm(request.POST, empregado=empregado)
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

        if form.is_valid():
            levantamento = form.save(commit=False)
            levantamento.empregado = empregado
            levantamento.empresa = empregado.empresa

            quantidade_levantada = levantamento.quantidade or 0

            if quantidade_levantada <= 0:
                form.add_error("quantidade", "A quantidade deve ser superior a zero.")
            else:
                with transaction.atomic():
                    material_levantamento = get_object_or_404(
                        Material.objects.select_for_update(),
                        id=levantamento.material_id,
                        empresa_id=empregado.empresa_id,
                    )

                    if quantidade_levantada > (material_levantamento.quantidade or 0):
                        form.add_error("quantidade", "Quantidade insuficiente em stock para este levantamento.")
                    else:
                        furo_escolhido = form.cleaned_data.get("furo")
                        projeto_escolhido = form.cleaned_data.get("projeto")

                        levantamento.material = material_levantamento
                        levantamento.furo = furo_escolhido
                        levantamento.projeto = projeto_escolhido

                        if levantamento.furo and not levantamento.projeto:
                            levantamento.projeto = levantamento.furo.projeto

                        if not levantamento.projeto:
                            levantamento.projeto_id = material_levantamento.projeto_id

                        levantamento.save()

                        material_levantamento.quantidade = (material_levantamento.quantidade or 0) - quantidade_levantada

                        if material_levantamento.quantidade <= 0:
                            material_levantamento.quantidade = 0
                            if hasattr(material_levantamento, "estado"):
                                material_levantamento.estado = "sem_stock"
                        elif (
                            hasattr(material_levantamento, "stock_minimo")
                            and material_levantamento.stock_minimo is not None
                            and material_levantamento.quantidade <= material_levantamento.stock_minimo
                        ):
                            if hasattr(material_levantamento, "estado"):
                                material_levantamento.estado = "sem_stock"
                        elif hasattr(material_levantamento, "estado"):
                            material_levantamento.estado = "em_estoque"

                        material_levantamento.save()

                        logger.info(
                            "Levantamento registado com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s, levantamento_id=%s, material_id=%s, quantidade=%s",
                            request.user.id,
                            empregado.id,
                            empregado.empresa_id,
                            levantamento.id,
                            material_levantamento.id,
                            quantidade_levantada,
                        )
                        messages.success(request, "Levantamento registado com sucesso.")
                        return redirect("projetos:levantamento_list")
        else:
            logger.warning(
                "Erro ao registar levantamento. user_id=%s, empregado_id=%s, erros=%s",
                request.user.id,
                empregado.id,
                form.errors,
            )
            messages.error(request, "Erro ao registar levantamento.")

    else:
        initial = {}
        if material_id:
            initial["material"] = material_id
            if material_selecionado is not None and getattr(material_selecionado, "projeto_id", None):
                initial["projeto"] = material_selecionado.projeto_id

        form = LevantamentoMaterialForm(
            empregado=empregado,
            initial=initial,
        )
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

    return render(request, "projetos/levantamento_material_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Novo Levantamento de Material",
    })


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

    material_id = request.GET.get("material")
    material_selecionado = None

    if material_id:
        material_selecionado = get_object_or_404(
            Material,
            id=material_id,
            empresa_id=empregado.empresa_id,
        )

    if request.method == "POST":
        form = DevolucaoMaterialForm(request.POST, empregado=empregado)
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

        if form.is_valid():
            devolucao = form.save(commit=False)
            devolucao.empregado = empregado
            devolucao.empresa = empregado.empresa

            quantidade_devolvida = devolucao.quantidade or 0

            if quantidade_devolvida <= 0:
                form.add_error("quantidade", "A quantidade deve ser superior a zero.")
            else:
                with transaction.atomic():
                    material_devolucao = get_object_or_404(
                        Material.objects.select_for_update(),
                        id=devolucao.material_id,
                        empresa_id=empregado.empresa_id,
                    )

                    furo_escolhido = form.cleaned_data.get("furo")
                    projeto_escolhido = form.cleaned_data.get("projeto")

                    devolucao.material = material_devolucao
                    devolucao.furo = furo_escolhido
                    devolucao.projeto = projeto_escolhido

                    if devolucao.furo and not devolucao.projeto:
                        devolucao.projeto = devolucao.furo.projeto

                    if not devolucao.projeto:
                        devolucao.projeto_id = material_devolucao.projeto_id

                    devolucao.save()

                    material_devolucao.quantidade = (material_devolucao.quantidade or 0) + quantidade_devolvida

                    if (
                        hasattr(material_devolucao, "stock_minimo")
                        and material_devolucao.stock_minimo is not None
                        and material_devolucao.quantidade <= material_devolucao.stock_minimo
                    ):
                        if hasattr(material_devolucao, "estado"):
                            material_devolucao.estado = "sem_stock"
                    elif hasattr(material_devolucao, "estado"):
                        material_devolucao.estado = "em_estoque"

                    material_devolucao.save()

                logger.info(
                    "Devolução registada com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s, devolucao_id=%s, material_id=%s, quantidade=%s",
                    request.user.id,
                    empregado.id,
                    empregado.empresa_id,
                    devolucao.id,
                    material_devolucao.id,
                    quantidade_devolvida,
                )
                messages.success(request, "Devolução registada com sucesso.")
                return redirect("projetos:devolucao_material_list")
        else:
            logger.warning(
                "Erro ao registar devolução. user_id=%s, empregado_id=%s, erros=%s",
                request.user.id,
                empregado.id,
                form.errors,
            )
            messages.error(request, "Erro ao registar devolução.")
    else:
        initial = {}
        if material_id:
            initial["material"] = material_id
            if material_selecionado is not None and getattr(material_selecionado, "projeto_id", None):
                initial["projeto"] = material_selecionado.projeto_id

        form = DevolucaoMaterialForm(
            empregado=empregado,
            initial=initial,
        )
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

    return render(request, "projetos/devolucao_material_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Nova Devolução de Material",
    })


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
