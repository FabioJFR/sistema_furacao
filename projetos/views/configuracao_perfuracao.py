import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError

from core.permissions import admin_required
from plataforma.models import PerfilPlataforma
from projetos.decorators import empregado_required
from projetos.forms.configuracao_perfuracao import ConfiguracaoPerfuracaoEmpregadoForm
from projetos.models import ConfiguracaoPerfuracaoEmpregado, Empregados
from projetos.models import HistoricoConfiguracaoPerfuracao
from projetos.selectors.historico_configuracao import (
    obter_historico_configuracao_por_configuracao,
    obter_ultimo_historico_da_configuracao,
)

logger = logging.getLogger("core")


ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


# ---------------- HELPERS ----------------
def _obter_contexto_admin_configuracao(request):
    logger.debug(
        "A resolver contexto administrativo em configuracao_perfuracao.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    admin_empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
    if admin_empregado:
        logger.info(
            "Contexto administrativo resolvido via Empregados em configuracao_perfuracao.py. user_id=%s, empresa_id=%s",
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
            "Contexto administrativo resolvido via PerfilPlataforma em configuracao_perfuracao.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em configuracao_perfuracao.py. user_id=%s",
        request.user.id,
    )
    return None



def _obter_empresa_admin_configuracao(request):
    contexto_admin = _obter_contexto_admin_configuracao(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or not empresa:
        logger.warning(
            "Contexto administrativo sem empresa em configuracao_perfuracao.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, None



def _obter_empregado_autenticado_configuracao(request):
    logger.debug(
        "A resolver empregado autenticado em configuracao_perfuracao.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
    if not empregado:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em configuracao_perfuracao.py. user_id=%s",
            request.user.id,
        )
        messages.error(
            request,
            "A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        )
        return None, redirect("projetos:redirect_after_login")

    if not empregado.empresa_id:
        logger.warning(
            "Empregado sem empresa associada em configuracao_perfuracao.py. user_id=%s, empregado_id=%s",
            request.user.id,
            empregado.id,
        )
        messages.error(request, "A tua conta não está associada a uma empresa. Contacta o administrador.")
        return None, redirect("projetos:redirect_after_login")

    return empregado, None


# ============================================================
# EMPREGADO
# ============================================================

# Multiempresa: a configuração de perfuração deve ser sempre listada, editada e apagada dentro da empresa do utilizador.
@login_required
@empregado_required
def configuracao_perfuracao_list_empregado(request):
    logger.info(
        "Entrada na view configuracao_perfuracao_list_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_configuracao(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_list_empregado. user_id=%s", request.user.id)
        return resposta_erro

    configuracoes = (
        ConfiguracaoPerfuracaoEmpregado.objects
        .filter(empregado=empregado, empresa=empregado.empresa)
        .select_related("furo", "atualizado_por")
        .order_by("furo__nome")
    )

    logger.info(
        "View configuracao_perfuracao_list_empregado carregada com sucesso. user_id=%s, empregado_id=%s, total_configuracoes=%s",
        request.user.id,
        empregado.id,
        configuracoes.count() if hasattr(configuracoes, "count") else "n/a",
    )
    return render(request, "projetos/configuracao_perfuracao_list_empregado.html", {
        "empregado": empregado,
        "configuracoes": configuracoes,
    })


@login_required
@empregado_required
def configuracao_perfuracao_create_empregado(request):
    logger.info(
        "Entrada na view configuracao_perfuracao_create_empregado. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_configuracao(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_create_empregado. user_id=%s", request.user.id)
        return resposta_erro

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(request.POST, empregado=empregado)
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa
        form.instance.atualizado_por = request.user

        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.empresa = empregado.empresa
            configuracao.atualizado_por = request.user
            try:
                configuracao.save()
            except ValidationError as e:
                if hasattr(e, "message_dict"):
                    for campo, erros in e.message_dict.items():
                        for erro in erros:
                            form.add_error(campo, erro)
                else:
                    form.add_error(None, e)
            else:
                HistoricoConfiguracaoPerfuracao.registar_historico(
                    configuracao=configuracao,
                    acao="criado",
                    utilizador=request.user,
                    observacoes="Configuração criada."
                )

                logger.info(
                    "Configuração de perfuração criada com sucesso por empregado. user_id=%s, empregado_id=%s, configuracao_id=%s",
                    request.user.id,
                    empregado.id,
                    configuracao.id,
                )
                messages.success(request, "Configuração de perfuração criada com sucesso.")
                return redirect("projetos:configuracao_perfuracao_list_empregado")

        logger.warning(
            "Erro ao criar configuração de perfuração por empregado. user_id=%s, empregado_id=%s, erros=%s",
            request.user.id,
            empregado.id,
            form.errors,
        )
        messages.error(request, "Erro ao criar a configuração de perfuração. Verifique os dados.")
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(empregado=empregado)

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "titulo": "Nova Configuração de Perfuração",
        "modo_admin": False,
        "empregado_obj": empregado,
    })


@login_required
@empregado_required
def configuracao_perfuracao_update_empregado(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_update_empregado. user_id=%s, username='%s', configuracao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_configuracao(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_update_empregado. user_id=%s", request.user.id)
        return resposta_erro

    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado,
        pk=pk,
        empregado=empregado,
        empresa=empregado.empresa,
    )

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            request.POST,
            instance=configuracao,
            empregado=empregado
        )
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa
        form.instance.atualizado_por = request.user

        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.empresa = empregado.empresa
            configuracao.atualizado_por = request.user
            try:
                configuracao.save()
            except ValidationError as e:
                if hasattr(e, "message_dict"):
                    for campo, erros in e.message_dict.items():
                        for erro in erros:
                            form.add_error(campo, erro)
                else:
                    form.add_error(None, e)
            else:
                HistoricoConfiguracaoPerfuracao.registar_historico(
                    configuracao=configuracao,
                    acao="editado",
                    utilizador=request.user,
                    observacoes="Configuração editada."
                )

                logger.info(
                    "Configuração de perfuração atualizada com sucesso por empregado. user_id=%s, empregado_id=%s, configuracao_id=%s",
                    request.user.id,
                    empregado.id,
                    configuracao.id,
                )
                messages.success(request, "Configuração de perfuração atualizada com sucesso.")
                return redirect("projetos:configuracao_perfuracao_list_empregado")

        logger.warning(
            "Erro ao atualizar configuração de perfuração por empregado. user_id=%s, configuracao_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar a configuração de perfuração. Verifique os dados.")
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            instance=configuracao,
            empregado=empregado
        )

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "titulo": "Editar Configuração de Perfuração",
        "modo_admin": False,
        "empregado_obj": empregado,
        "configuracao": configuracao,
    })


@login_required
@empregado_required
def configuracao_perfuracao_delete_empregado(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_delete_empregado. user_id=%s, username='%s', configuracao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_configuracao(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_delete_empregado. user_id=%s", request.user.id)
        return resposta_erro

    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado,
        pk=pk,
        empregado=empregado,
        empresa=empregado.empresa,
    )

    if request.method == "POST":
        HistoricoConfiguracaoPerfuracao.registar_historico(
            configuracao=configuracao,
            acao="apagado",
            utilizador=request.user,
            observacoes="Configuração apagada."
        )
        configuracao_id = configuracao.id
        configuracao.delete()
        logger.info(
            "Configuração de perfuração apagada com sucesso por empregado. user_id=%s, empregado_id=%s, configuracao_id=%s",
            request.user.id,
            empregado.id,
            configuracao_id,
        )
        messages.success(request, "Configuração de perfuração apagada com sucesso.")
        return redirect("projetos:configuracao_perfuracao_list_empregado")

    return render(request, "projetos/configuracao_perfuracao_confirm_delete.html", {
        "configuracao": configuracao,
        "modo_admin": False,
        "empregado_obj": empregado,
    })


# ============================================================
# ADMIN
# ============================================================

@login_required
@admin_required
def configuracao_perfuracao_list_admin(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_list_admin. user_id=%s, username='%s', empregado_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, resposta_erro = _obter_empresa_admin_configuracao(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_list_admin. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)

    configuracoes = (
        ConfiguracaoPerfuracaoEmpregado.objects
        .filter(empregado=empregado, empresa=empresa)
        .select_related("furo", "atualizado_por")
        .order_by("furo__nome")
    )

    logger.info(
        "View configuracao_perfuracao_list_admin carregada com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, total_configuracoes=%s",
        request.user.id,
        empresa.id,
        empregado.id,
        configuracoes.count() if hasattr(configuracoes, "count") else "n/a",
    )
    return render(request, "projetos/configuracao_perfuracao_list_admin.html", {
        "empregado_obj": empregado,
        "configuracoes": configuracoes,
    })


@login_required
@admin_required
def configuracao_perfuracao_create_admin(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_create_admin. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_configuracao(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_create_admin. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(request.POST, empregado=empregado)
        form.instance.empregado = empregado
        form.instance.empresa = empresa
        form.instance.atualizado_por = request.user

        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.empresa = empresa
            configuracao.atualizado_por = request.user
            try:
                configuracao.save()
            except ValidationError as e:
                if hasattr(e, "message_dict"):
                    for campo, erros in e.message_dict.items():
                        for erro in erros:
                            form.add_error(campo, erro)
                else:
                    form.add_error(None, e)
            else:
                HistoricoConfiguracaoPerfuracao.registar_historico(
                    configuracao=configuracao,
                    acao="criado",
                    utilizador=request.user,
                    observacoes="Configuração criada pelo administrador."
                )

                logger.info(
                    "Configuração de perfuração criada com sucesso por admin. user_id=%s, empresa_id=%s, empregado_id=%s, configuracao_id=%s",
                    request.user.id,
                    empresa.id,
                    empregado.id,
                    configuracao.id,
                )
                messages.success(request, "Configuração de perfuração criada com sucesso.")
                return redirect("projetos:configuracao_perfuracao_list_admin", pk=empregado.pk)

        logger.warning(
            "Erro ao criar configuração de perfuração por admin. user_id=%s, empregado_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao criar a configuração de perfuração. Verifique os dados.")
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(empregado=empregado)

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "titulo": f"Nova Configuração de Perfuração - {empregado.nome}",
        "modo_admin": True,
        "empregado_obj": empregado,
    })


@login_required
@admin_required
def configuracao_perfuracao_update_admin(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_update_admin. user_id=%s, username='%s', configuracao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_configuracao(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_update_admin. user_id=%s", request.user.id)
        return resposta_erro

    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado.objects.select_related("empregado"),
        pk=pk,
        empresa=empresa,
    )
    empregado = configuracao.empregado

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            request.POST,
            instance=configuracao,
            empregado=empregado
        )
        form.instance.empregado = empregado
        form.instance.empresa = empresa
        form.instance.atualizado_por = request.user

        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.empresa = empresa
            configuracao.atualizado_por = request.user
            try:
                configuracao.save()
            except ValidationError as e:
                if hasattr(e, "message_dict"):
                    for campo, erros in e.message_dict.items():
                        for erro in erros:
                            form.add_error(campo, erro)
                else:
                    form.add_error(None, e)
            else:
                HistoricoConfiguracaoPerfuracao.registar_historico(
                    configuracao=configuracao,
                    acao="editado",
                    utilizador=request.user,
                    observacoes="Configuração editada pelo administrador."
                )

                logger.info(
                    "Configuração de perfuração atualizada com sucesso por admin. user_id=%s, empresa_id=%s, empregado_id=%s, configuracao_id=%s",
                    request.user.id,
                    empresa.id,
                    empregado.id,
                    configuracao.id,
                )
                messages.success(request, "Configuração de perfuração atualizada com sucesso.")
                return redirect("projetos:configuracao_perfuracao_list_admin", pk=empregado.pk)

        logger.warning(
            "Erro ao atualizar configuração de perfuração por admin. user_id=%s, configuracao_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar a configuração de perfuração. Verifique os dados.")
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            instance=configuracao,
            empregado=empregado
        )

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "titulo": f"Editar Configuração de Perfuração - {empregado.nome}",
        "modo_admin": True,
        "empregado_obj": empregado,
        "configuracao": configuracao,
    })


@login_required
@admin_required
def configuracao_perfuracao_delete_admin(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_delete_admin. user_id=%s, username='%s', configuracao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_configuracao(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_delete_admin. user_id=%s", request.user.id)
        return resposta_erro

    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado.objects.select_related("empregado", "furo"),
        pk=pk,
        empresa=empresa,
    )
    empregado = configuracao.empregado

    if request.method == "POST":
        HistoricoConfiguracaoPerfuracao.registar_historico(
            configuracao=configuracao,
            acao="apagado",
            utilizador=request.user,
            observacoes="Configuração apagada pelo administrador."
        )
        configuracao_id = configuracao.id
        configuracao.delete()
        logger.info(
            "Configuração de perfuração apagada com sucesso por admin. user_id=%s, empresa_id=%s, empregado_id=%s, configuracao_id=%s",
            request.user.id,
            empresa.id,
            empregado.id,
            configuracao_id,
        )
        messages.success(request, "Configuração de perfuração apagada com sucesso.")
        return redirect("projetos:configuracao_perfuracao_list_admin", pk=empregado.pk)

    return render(request, "projetos/configuracao_perfuracao_confirm_delete.html", {
        "configuracao": configuracao,
        "modo_admin": True,
        "empregado_obj": empregado,
    })

@login_required
@empregado_required
def configuracao_perfuracao_detail_empregado(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_detail_empregado. user_id=%s, username='%s', configuracao_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_configuracao(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_detail_empregado. user_id=%s", request.user.id)
        return resposta_erro

    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado.objects.select_related(
            "empregado", "furo", "atualizado_por"
        ),
        pk=pk,
        empregado=empregado,
        empresa=empregado.empresa,
    )

    historicos = obter_historico_configuracao_por_configuracao(configuracao, empresa=empregado.empresa)
    ultimo_historico = obter_ultimo_historico_da_configuracao(configuracao, empresa=empregado.empresa)

    logger.info(
        "View configuracao_perfuracao_detail_empregado carregada com sucesso. user_id=%s, empregado_id=%s, configuracao_id=%s",
        request.user.id,
        empregado.id,
        configuracao.id,
    )
    return render(request, "projetos/configuracao_perfuracao_detail.html", {
        "configuracao": configuracao,
        "historicos": historicos[:5],
        "ultimo_historico": ultimo_historico,
        "modo_admin": False,
        "empregado_obj": empregado,
    })


@login_required
@admin_required
def configuracao_perfuracao_detail_admin(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_detail_admin. user_id=%s, username='%s', configuracao_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, resposta_erro = _obter_empresa_admin_configuracao(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_detail_admin. user_id=%s", request.user.id)
        return resposta_erro

    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado.objects.select_related(
            "empregado", "furo", "atualizado_por"
        ),
        pk=pk,
        empresa=empresa,
    )

    historicos = obter_historico_configuracao_por_configuracao(configuracao, empresa=empresa)
    ultimo_historico = obter_ultimo_historico_da_configuracao(configuracao, empresa=empresa)

    logger.info(
        "View configuracao_perfuracao_detail_admin carregada com sucesso. user_id=%s, empresa_id=%s, configuracao_id=%s",
        request.user.id,
        empresa.id,
        configuracao.id,
    )
    return render(request, "projetos/configuracao_perfuracao_detail.html", {
        "configuracao": configuracao,
        "historicos": historicos[:5],
        "ultimo_historico": ultimo_historico,
        "modo_admin": True,
        "empregado_obj": configuracao.empregado,
    })