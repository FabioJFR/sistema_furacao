import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.permissions import admin_required
from projetos.decorators import empregado_required
from projetos.forms.configuracao_perfuracao import ConfiguracaoPerfuracaoEmpregadoForm
from projetos.selectors.configuracao_perfuracao import (
    obter_configuracao_perfuracao_admin,
    obter_configuracao_perfuracao_empregado,
    obter_configuracao_perfuracao_furo_empregado,
    obter_empregado_por_pk_empresa,
    obter_lista_configuracoes_perfuracao_empregado,
)
from projetos.selectors.forms import listar_furos_configuracao_perfuracao_qs
from projetos.selectors.historico_configuracao import (
    obter_historico_configuracao_por_configuracao,
    obter_ultimo_historico_da_configuracao,
)
from projetos.services.configuracao_perfuracao import (
    apagar_configuracao_perfuracao,
    processar_fluxo_form_configuracao_perfuracao,
)
from projetos.services.acesso_contexto import (
    obter_empregado_autenticado_contexto,
    obter_empresa_admin_contexto,
)

logger = logging.getLogger("core")


# ---------------- HELPERS ----------------
def _obter_empresa_admin_configuracao(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        logger.warning(
            "Falha ao resolver empresa administrativa em configuracao_perfuracao.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empresa, None



def _obter_empregado_autenticado_configuracao(request):
    logger.debug(
        "A resolver empregado autenticado em configuracao_perfuracao.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado, _ligado_por_fallback, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
        vincular_por_email=True,
    )
    if resposta_erro:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em configuracao_perfuracao.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empregado, None


def _processar_form_configuracao(
    *,
    request,
    empresa,
    empregado,
    resultado,
    sucesso_msg,
    erro_msg,
    log_sucesso,
    log_erro,
    redirect_name,
    redirect_kwargs,
):
    if not resultado["ok"]:
        logger.warning(log_erro, request.user.id, resultado.get("erros_form"))
        messages.error(request, erro_msg)
        return None

    configuracao = resultado["configuracao"]

    logger.info(log_sucesso, request.user.id, empresa.id, empregado.id, configuracao.id)
    messages.success(request, sucesso_msg)
    return redirect(redirect_name, **redirect_kwargs)


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

    configuracoes = obter_lista_configuracoes_perfuracao_empregado(
        empregado,
        empresa=empregado.empresa,
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

    furo_inicial = None
    furo_id = request.POST.get("furo") if request.method == "POST" else request.GET.get("furo")
    configuracao_existente = None
    if furo_id:
        furo_inicial = (
            listar_furos_configuracao_perfuracao_qs(empregado=empregado, empresa=empregado.empresa)
            .filter(pk=furo_id)
            .first()
        )
        if furo_inicial:
            configuracao_existente = obter_configuracao_perfuracao_furo_empregado(
                furo=furo_inicial,
                empregado=empregado,
            )
            if configuracao_existente and request.method == "GET":
                return redirect("projetos:configuracao_perfuracao_update_empregado", pk=configuracao_existente.pk)

    fluxo = processar_fluxo_form_configuracao_perfuracao(
        request_method=request.method,
        post_data=request.POST,
        form_class=ConfiguracaoPerfuracaoEmpregadoForm,
        empregado=empregado,
        empresa=empregado.empresa,
        atualizado_por=request.user,
        instance=configuracao_existente,
        initial={"furo": furo_inicial} if furo_inicial else None,
        acao_historico="editado" if configuracao_existente else "criado",
        observacoes_historico=(
            "Configuração editada a partir do formulário de criação."
            if configuracao_existente else
            "Configuração criada."
        ),
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        configuracao_foi_atualizada = bool(configuracao_existente)
        resposta = _processar_form_configuracao(
            request=request,
            empresa=empregado.empresa,
            empregado=empregado,
            resultado=resultado,
            sucesso_msg=(
                "Configuração de perfuração atualizada com sucesso."
                if configuracao_foi_atualizada else
                "Configuração de perfuração criada com sucesso."
            ),
            erro_msg="Erro ao criar a configuração de perfuração. Verifique os dados.",
            log_sucesso=(
                "Configuração de perfuração atualizada a partir do formulário de criação por empregado. user_id=%s, empresa_id=%s, empregado_id=%s, configuracao_id=%s"
                if configuracao_foi_atualizada else
                "Configuração de perfuração criada com sucesso por empregado. user_id=%s, empresa_id=%s, empregado_id=%s, configuracao_id=%s"
            ),
            log_erro="Erro ao criar configuração de perfuração por empregado. user_id=%s, erros=%s",
            redirect_name="projetos:configuracao_perfuracao_list_empregado",
            redirect_kwargs={},
        )
        if resposta:
            return resposta

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

    configuracao = obter_configuracao_perfuracao_empregado(pk, empregado)

    fluxo = processar_fluxo_form_configuracao_perfuracao(
        request_method=request.method,
        post_data=request.POST,
        form_class=ConfiguracaoPerfuracaoEmpregadoForm,
        empregado=empregado,
        empresa=empregado.empresa,
        atualizado_por=request.user,
        instance=configuracao,
        acao_historico="editado",
        observacoes_historico="Configuração editada.",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta = _processar_form_configuracao(
            request=request,
            empresa=empregado.empresa,
            empregado=empregado,
            resultado=resultado,
            sucesso_msg="Configuração de perfuração atualizada com sucesso.",
            erro_msg="Erro ao atualizar a configuração de perfuração. Verifique os dados.",
            log_sucesso="Configuração de perfuração atualizada com sucesso por empregado. user_id=%s, empresa_id=%s, empregado_id=%s, configuracao_id=%s",
            log_erro="Erro ao atualizar configuração de perfuração por empregado. user_id=%s, erros=%s",
            redirect_name="projetos:configuracao_perfuracao_list_empregado",
            redirect_kwargs={},
        )
        if resposta:
            return resposta

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

    configuracao = obter_configuracao_perfuracao_empregado(pk, empregado)

    if request.method == "POST":
        configuracao_id = apagar_configuracao_perfuracao(
            configuracao=configuracao,
            utilizador=request.user,
            observacoes_historico="Configuração apagada.",
        )
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

    empregado = obter_empregado_por_pk_empresa(pk, empresa)
    configuracoes = obter_lista_configuracoes_perfuracao_empregado(
        empregado,
        empresa=empresa,
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

    empregado = obter_empregado_por_pk_empresa(pk, empresa)

    fluxo = processar_fluxo_form_configuracao_perfuracao(
        request_method=request.method,
        post_data=request.POST,
        form_class=ConfiguracaoPerfuracaoEmpregadoForm,
        empregado=empregado,
        empresa=empresa,
        atualizado_por=request.user,
        acao_historico="criado",
        observacoes_historico="Configuração criada pelo administrador.",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta = _processar_form_configuracao(
            request=request,
            empresa=empresa,
            empregado=empregado,
            resultado=resultado,
            sucesso_msg="Configuração de perfuração criada com sucesso.",
            erro_msg="Erro ao criar a configuração de perfuração. Verifique os dados.",
            log_sucesso="Configuração de perfuração criada com sucesso por admin. user_id=%s, empresa_id=%s, empregado_id=%s, configuracao_id=%s",
            log_erro="Erro ao criar configuração de perfuração por admin. user_id=%s, erros=%s",
            redirect_name="projetos:configuracao_perfuracao_list_admin",
            redirect_kwargs={"pk": empregado.pk},
        )
        if resposta:
            return resposta

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

    configuracao = obter_configuracao_perfuracao_admin(pk, empresa)
    empregado = configuracao.empregado

    fluxo = processar_fluxo_form_configuracao_perfuracao(
        request_method=request.method,
        post_data=request.POST,
        form_class=ConfiguracaoPerfuracaoEmpregadoForm,
        empregado=empregado,
        empresa=empresa,
        atualizado_por=request.user,
        instance=configuracao,
        acao_historico="editado",
        observacoes_historico="Configuração editada pelo administrador.",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta = _processar_form_configuracao(
            request=request,
            empresa=empresa,
            empregado=empregado,
            resultado=resultado,
            sucesso_msg="Configuração de perfuração atualizada com sucesso.",
            erro_msg="Erro ao atualizar a configuração de perfuração. Verifique os dados.",
            log_sucesso="Configuração de perfuração atualizada com sucesso por admin. user_id=%s, empresa_id=%s, empregado_id=%s, configuracao_id=%s",
            log_erro="Erro ao atualizar configuração de perfuração por admin. user_id=%s, erros=%s",
            redirect_name="projetos:configuracao_perfuracao_list_admin",
            redirect_kwargs={"pk": empregado.pk},
        )
        if resposta:
            return resposta

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

    configuracao = obter_configuracao_perfuracao_admin(pk, empresa)
    empregado = configuracao.empregado

    if request.method == "POST":
        configuracao_id = apagar_configuracao_perfuracao(
            configuracao=configuracao,
            utilizador=request.user,
            observacoes_historico="Configuração apagada pelo administrador.",
        )
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

    configuracao = obter_configuracao_perfuracao_empregado(pk, empregado)

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

    configuracao = obter_configuracao_perfuracao_admin(pk, empresa)

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
