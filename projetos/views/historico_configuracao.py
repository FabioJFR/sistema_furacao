import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.permissions import admin_required
from projetos.decorators import empregado_required
from projetos.selectors.acesso import obter_contexto_admin_projetos, obter_empregado_por_user
from projetos.selectors.historico_configuracao import (
    obter_empregado_historico_por_pk_empresa,
    obter_furo_historico_por_pk_empresa,
    obter_historico_anterior,
    obter_historico_configuracao_por_configuracao,
    obter_historico_configuracao_por_empregado,
    obter_historico_configuracao_por_furo,
    obter_historico_configuracao_por_pk,
)
from projetos.services.historico_configuracao_perfuracao import restaurar_configuracao_a_partir_historico

logger = logging.getLogger("core")


ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


# Multiempresa: histórico de configuração deve ser sempre visto e restaurado apenas dentro da empresa do utilizador.


# ---------------- HELPERS ----------------
def _obter_contexto_admin_historico(request):
    logger.debug(
        "A resolver contexto administrativo em historico_configuracao.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    perfil = obter_contexto_admin_projetos(request.user)

    if perfil:
        logger.info(
            "Contexto administrativo resolvido via PerfilPlataforma em historico_configuracao.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em historico_configuracao.py. user_id=%s",
        request.user.id,
    )
    return None



def _obter_empresa_admin_historico(request):
    contexto_admin = _obter_contexto_admin_historico(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or not empresa:
        logger.warning(
            "Contexto administrativo sem empresa em historico_configuracao.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, None



def _obter_empregado_autenticado_historico(request):
    logger.debug(
        "A resolver empregado autenticado em historico_configuracao.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado = obter_empregado_por_user(request.user)
    if not empregado:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em historico_configuracao.py. user_id=%s",
            request.user.id,
        )
        messages.error(
            request,
            "A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        )
        return None, redirect("projetos:redirect_after_login")

    if not empregado.empresa_id:
        logger.warning(
            "Empregado sem empresa associada em historico_configuracao.py. user_id=%s, empregado_id=%s",
            request.user.id,
            empregado.id,
        )
        messages.error(request, "A tua conta não está associada a uma empresa. Contacta o administrador.")
        return None, redirect("projetos:redirect_after_login")

    return empregado, None



def _utilizador_pode_ver_historico(request, historico):
    contexto_admin = _obter_contexto_admin_historico(request)
    if contexto_admin:
        empresa_id = getattr(contexto_admin, "empresa_id", None)
        permitido = bool(empresa_id and historico.empresa_id == empresa_id)
        if permitido:
            logger.info(
                "Acesso ao histórico autorizado via contexto admin. user_id=%s, historico_id=%s, empresa_id=%s",
                request.user.id,
                historico.pk,
                empresa_id,
            )
        return permitido, True

    empregado, _ = _obter_empregado_autenticado_historico(request)
    permitido = bool(
        empregado and
        empregado.empresa_id and
        historico.empregado_id == empregado.id and
        historico.empresa_id == empregado.empresa_id
    )
    if permitido:
        logger.info(
            "Acesso ao histórico autorizado via empregado. user_id=%s, empregado_id=%s, historico_id=%s",
            request.user.id,
            empregado.id,
            historico.pk,
        )
    return permitido, False


@login_required
@empregado_required
def historico_configuracao_list_empregado(request):
    logger.info(
        "Entrada na view historico_configuracao_list_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_historico(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view historico_configuracao_list_empregado. user_id=%s", request.user.id)
        return resposta_erro

    historicos = obter_historico_configuracao_por_empregado(empregado, empresa=empregado.empresa)

    logger.info(
        "View historico_configuracao_list_empregado carregada com sucesso. user_id=%s, empregado_id=%s, total_historicos=%s",
        request.user.id,
        empregado.id,
        historicos.count() if hasattr(historicos, "count") else "n/a",
    )
    return render(request, "projetos/historico_configuracao_list_empregado.html", {
        "empregado": empregado,
        "historicos": historicos,
    })


@login_required
@admin_required
def historico_configuracao_list_admin(request, pk):
    logger.info(
        "Entrada na view historico_configuracao_list_admin. user_id=%s, username='%s', empregado_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, resposta_erro = _obter_empresa_admin_historico(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view historico_configuracao_list_admin. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_historico_por_pk_empresa(pk, empresa)
    historicos = obter_historico_configuracao_por_empregado(empregado, empresa=empresa)

    logger.info(
        "View historico_configuracao_list_admin carregada com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, total_historicos=%s",
        request.user.id,
        empresa.id,
        empregado.id,
        historicos.count() if hasattr(historicos, "count") else "n/a",
    )
    return render(request, "projetos/historico_configuracao_list_admin.html", {
        "empregado_obj": empregado,
        "historicos": historicos,
    })


@login_required
@admin_required
def historico_configuracao_list_furo_admin(request, furo_id):
    logger.info(
        "Entrada na view historico_configuracao_list_furo_admin. user_id=%s, username='%s', furo_id=%s",
        request.user.id,
        request.user.username,
        furo_id,
    )
    empresa, resposta_erro = _obter_empresa_admin_historico(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view historico_configuracao_list_furo_admin. user_id=%s", request.user.id)
        return resposta_erro

    furo = obter_furo_historico_por_pk_empresa(furo_id, empresa)
    historicos = obter_historico_configuracao_por_furo(furo, empresa=empresa)

    logger.info(
        "View historico_configuracao_list_furo_admin carregada com sucesso. user_id=%s, empresa_id=%s, furo_id=%s, total_historicos=%s",
        request.user.id,
        empresa.id,
        furo.id,
        historicos.count() if hasattr(historicos, "count") else "n/a",
    )
    return render(request, "projetos/historico_configuracao_list_furo_admin.html", {
        "furo": furo,
        "historicos": historicos,
    })


@login_required
def historico_configuracao_detail(request, pk):
    logger.info(
        "Entrada na view historico_configuracao_detail. user_id=%s, username='%s', historico_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    historico = obter_historico_configuracao_por_pk(pk)

    permitido, _is_admin = _utilizador_pode_ver_historico(request, historico)
    if not permitido:
        logger.warning(
            "Acesso negado na view historico_configuracao_detail. user_id=%s, historico_pk=%s",
            request.user.id,
            pk,
        )
        messages.error(request, "Não tens permissão para ver este histórico.")
        return redirect("projetos:redirect_after_login")

    historico_anterior = obter_historico_anterior(historico, empresa=historico.empresa)

    logger.info(
        "View historico_configuracao_detail carregada com sucesso. user_id=%s, historico_id=%s",
        request.user.id,
        historico.pk,
    )
    return render(request, "projetos/historico_configuracao_detail.html", {
        "historico": historico,
        "historico_anterior": historico_anterior,
    })


@login_required
def historico_configuracao_comparar(request, pk):
    logger.info(
        "Entrada na view historico_configuracao_comparar. user_id=%s, username='%s', historico_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    historico = obter_historico_configuracao_por_pk(pk)

    permitido, _is_admin = _utilizador_pode_ver_historico(request, historico)
    if not permitido:
        logger.warning(
            "Acesso negado na view historico_configuracao_comparar. user_id=%s, historico_pk=%s",
            request.user.id,
            pk,
        )
        messages.error(request, "Não tens permissão para comparar este histórico.")
        return redirect("projetos:redirect_after_login")

    anterior = obter_historico_anterior(historico, empresa=historico.empresa)

    campos = [
        ("comprimento_tubo", "Tubo"),
        ("comprimento_karoutier", "Karoutier"),
        ("quantidade_karoutier", "Qtd. Karoutier"),
        ("comprimento_acrescento", "Acrescento"),
        ("quantidade_acrescento", "Qtd. Acrescento"),
        ("comprimento_calibrador", "Calibrador"),
        ("quantidade_calibrador", "Qtd. Calibrador"),
        ("comprimento_record", "Record"),
        ("quantidade_record", "Qtd. Record"),
        ("comprimento_bit", "Bit"),
        ("comprimento_caixa_mola", "Caixa de mola"),
        ("comprimento_tubo_interior", "Tubo interior"),
        ("quantidade_tubo_interior", "Qtd. Tubo interior"),
        ("comprimento_acrescento_tubo_interior", "Acrescento do tubo interior"),
        ("quantidade_acrescento_tubo_interior", "Qtd. Acrescento do tubo interior"),
        ("comprimento_cabeca_interior", "Cabeça de interior"),
    ]

    comparacao = []

    for campo, label in campos:
        valor_atual = getattr(historico, campo, None)
        valor_anterior = getattr(anterior, campo, None) if anterior else None
        alterado = valor_atual != valor_anterior

        comparacao.append({
            "campo": campo,
            "label": label,
            "anterior": valor_anterior,
            "atual": valor_atual,
            "alterado": alterado,
        })

    logger.info(
        "View historico_configuracao_comparar carregada com sucesso. user_id=%s, historico_id=%s",
        request.user.id,
        historico.pk,
    )
    return render(request, "projetos/historico_configuracao_comparar.html", {
        "historico": historico,
        "historico_anterior": anterior,
        "comparacao": comparacao,
    })


@login_required
def historico_configuracao_restaurar(request, pk):
    logger.info(
        "Entrada na view historico_configuracao_restaurar. user_id=%s, username='%s', historico_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    historico = obter_historico_configuracao_por_pk(pk)

    permitido, is_admin = _utilizador_pode_ver_historico(request, historico)
    if not permitido:
        logger.warning(
            "Acesso negado na view historico_configuracao_restaurar. user_id=%s, historico_pk=%s",
            request.user.id,
            pk,
        )
        messages.error(request, "Não tens permissão para restaurar este histórico.")
        return redirect("projetos:redirect_after_login")

    if request.method == "POST":
        configuracao = restaurar_configuracao_a_partir_historico(
            historico=historico,
            utilizador=request.user,
        )

        logger.info(
            "Histórico restaurado com sucesso. user_id=%s, historico_id=%s, configuracao_id=%s",
            request.user.id,
            historico.pk,
            configuracao.pk,
        )
        messages.success(request, "Versão restaurada com sucesso.")

        if is_admin:
            return redirect("projetos:configuracao_perfuracao_list_admin", pk=historico.empregado.pk)

        return redirect("projetos:configuracao_perfuracao_list_empregado")

    return render(request, "projetos/historico_configuracao_restaurar.html", {
        "historico": historico,
    })
