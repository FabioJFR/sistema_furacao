import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from core.permissions import admin_required
from ..decorators import empregado_required

from projetos.forms.registo import (
    RegistoDiarioEmpregadoAdminForm,
    RegistoDiarioEmpregadoForm,
)
from projetos.selectors.acesso import obter_contexto_admin_projetos, obter_empregado_por_user
from projetos.selectors.registos import (
    obter_contexto_filtros_registos_admin,
    obter_registo_admin,
    obter_registo_empregado,
    obter_registos_admin_filtrados,
    obter_registos_empregado,
)
from projetos.services.registos import (
    anexar_fotos_amostra,
    atualizar_registo_diario,
    atualizar_registo_diario_empregado,
    criar_registo_diario,
)

logger = logging.getLogger("core")


# -------- REGISTOS --------------


# ---------------- HELPERS ----------------
def _obter_contexto_admin_registos(request):
    logger.debug(
        "A resolver contexto administrativo em registos.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    perfil = obter_contexto_admin_projetos(request.user)
    if perfil:
        logger.info(
            "Contexto administrativo resolvido via PerfilPlataforma em registos.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em registos.py. user_id=%s",
        request.user.id,
    )
    return None



def _obter_empresa_admin_registos(request):
    contexto_admin = _obter_contexto_admin_registos(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or not empresa:
        logger.warning(
            "Contexto administrativo sem empresa em registos.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, None



def _obter_empregado_autenticado_registos(request):
    logger.debug(
        "A resolver empregado autenticado em registos.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado = obter_empregado_por_user(request.user)
    if not empregado:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em registos.py. user_id=%s",
            request.user.id,
        )
        messages.error(
            request,
            "A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        )
        return None, redirect("projetos:redirect_after_login")

    if not empregado.empresa_id:
        logger.warning(
            "Empregado sem empresa associada em registos.py. user_id=%s, empregado_id=%s",
            request.user.id,
            empregado.id,
        )
        messages.error(request, "A tua conta não está associada a uma empresa. Contacta o administrador.")
        return None, redirect("projetos:redirect_after_login")

    return empregado, None


@login_required
@empregado_required
def criar_registo_view(request):
    logger.info(
        "Entrada na view criar_registo_view. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    messages.info(
        request,
        "Este atalho antigo foi descontinuado. Use o formulário completo de registo diário."
    )
    return redirect("projetos:registos:create")


@login_required
@empregado_required
def registo_diario_list(request):
    logger.info(
        "Entrada na view registo_diario_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_registos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view registo_diario_list. user_id=%s", request.user.id)
        return resposta_erro

    registos = obter_registos_empregado(empregado)

    logger.info(
        "View registo_diario_list carregada com sucesso. user_id=%s, empregado_id=%s, total_registos=%s",
        request.user.id,
        empregado.id,
        registos.count() if hasattr(registos, "count") else "n/a",
    )
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
    logger.info(
        "Entrada na view registo_diario_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_registos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view registo_diario_create. user_id=%s", request.user.id)
        return resposta_erro

    if request.method == "POST":
        form = RegistoDiarioEmpregadoForm(
            request.POST,
            request.FILES,
            empregado=empregado,
        )
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

        if form.is_valid():
            registo = criar_registo_diario(form=form, empregado=empregado)
            anexar_fotos_amostra(
                registo=registo,
                empresa=empregado.empresa,
                fotos=request.FILES.getlist("fotos_amostra"),
            )

            logger.info(
                "Registo diário criado com sucesso. user_id=%s, empregado_id=%s, registo_id=%s",
                request.user.id,
                empregado.id,
                registo.id,
            )
            messages.success(request, "Registo diário guardado com sucesso.")
            return redirect("projetos:area_empregado")

        logger.warning(
            "Erro ao guardar registo diário. user_id=%s, empregado_id=%s, erros=%s",
            request.user.id,
            empregado.id,
            form.errors,
        )
        messages.error(request, "Erro ao guardar o registo diário. Verifique os dados.")
    else:
        form = RegistoDiarioEmpregadoForm(
            empregado=empregado,
            initial={"data": timezone.now().date()},
        )
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

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
    logger.info(
        "Entrada na view registo_diario_update. user_id=%s, username='%s', registo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_registos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view registo_diario_update. user_id=%s", request.user.id)
        return resposta_erro

    registo = obter_registo_empregado(empregado, pk)

    if request.method == "POST":
        form = RegistoDiarioEmpregadoForm(
            request.POST,
            request.FILES,
            instance=registo,
            empregado=empregado,
        )
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

        if form.is_valid():
            registo = atualizar_registo_diario_empregado(registo, form)
            anexar_fotos_amostra(
                registo=registo,
                empresa=empregado.empresa_id,
                fotos=request.FILES.getlist("fotos_amostra"),
            )

            logger.info(
                "Registo diário atualizado com sucesso por empregado. user_id=%s, empregado_id=%s, registo_id=%s",
                request.user.id,
                empregado.id,
                registo.id,
            )
            messages.success(request, "Registo diário atualizado com sucesso.")
            return redirect("projetos:registo_diario_list")

        logger.warning(
            "Erro ao atualizar registo diário por empregado. user_id=%s, registo_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar o registo diário.")
    else:
        form = RegistoDiarioEmpregadoForm(instance=registo, empregado=empregado)
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

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


# Multiempresa: o administrador só pode listar registos da sua própria empresa.
@login_required
@admin_required
def registos_admin_list(request):
    logger.info(
        "Entrada na view registos_admin_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view registos_admin_list. user_id=%s", request.user.id)
        return resposta_erro

    resultados = obter_registos_admin_filtrados(
        empresa=empresa,
        filtros=request.GET,
    )
    contexto_filtros = obter_contexto_filtros_registos_admin(empresa)
    registos = resultados["registos"]
    totais = resultados["totais"]

    logger.info(
        "View registos_admin_list carregada com sucesso. user_id=%s, empresa_id=%s, total_registos=%s",
        request.user.id,
        empresa.id,
        registos.count() if hasattr(registos, "count") else "n/a",
    )
    return render(
        request,
        "projetos/registos_admin_list.html",
        {
            "registos": registos,
            "empregados": contexto_filtros["empregados"],
            "projetos": contexto_filtros["projetos"],
            "furos": contexto_filtros["furos"],
            "filtros": resultados["filtros"],
            "total_horas": totais["total_horas"] or 0,
            "total_metros": totais["total_metros"] or 0,
            "total_paragem": totais["total_paragem"] or 0,
        },
    )


@login_required
@admin_required
def registo_admin_update(request, pk):
    logger.info(
        "Entrada na view registo_admin_update. user_id=%s, username='%s', registo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view registo_admin_update. user_id=%s", request.user.id)
        return resposta_erro

    registo = obter_registo_admin(empresa, pk)

    if request.method == "POST":
        form = RegistoDiarioEmpregadoAdminForm(
            request.POST,
            request.FILES,
            instance=registo,
        )

        if form.is_valid():
            atualizar_registo_diario(registo, form)
            anexar_fotos_amostra(
                registo=registo,
                empresa=empresa,
                fotos=request.FILES.getlist("fotos_amostra"),
            )

            logger.info(
                "Registo corrigido com sucesso por admin. user_id=%s, empresa_id=%s, registo_id=%s",
                request.user.id,
                empresa.id,
                registo.id,
            )
            messages.success(request, "Registo corrigido com sucesso.")
            return redirect("projetos:registos_admin_list")

        logger.warning(
            "Erro ao corrigir registo por admin. user_id=%s, registo_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
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
