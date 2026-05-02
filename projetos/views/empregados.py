import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Q

from django.urls import reverse

from projetos.models import (
    Empregados,
    Projeto,
    Furo,
    Material,
    EmpregadoFuro,
    EmpregadoProjeto,
    EmpregadoFicheiro,
    Medicao,
    RegistoDiarioEmpregado,
)
from ..decorators import admin_required, empregado_required
from ..forms.empregado import (
    EmpregadoCreateForm,
    EmpregadoFicheiroForm,
    EmpregadoProjetoForm,
    EmpregadoRegistroForm,
    EmpregadoUpdateForm,
)
from projetos.selectors.configuracao_perfuracao import (
    obter_lista_configuracoes_perfuracao_empregado,
)
from projetos.selectors.acesso import (
    obter_individual_por_user,
    obter_perfil_ativo_por_user,
    resolver_empregado_por_user_ou_email,
)
from projetos.services.acesso_contexto import (
    obter_empregado_autenticado_contexto,
    obter_empresa_admin_contexto,
)
from projetos.selectors.empregados import (
    empregado_tem_acesso_furo,
    empregado_tem_acesso_projeto,
    obter_contexto_area_empregado,
    obter_furo_empregado,
    obter_furos_projeto_empregado,
    obter_lista_furos_empregado,
    obter_lista_medicoes_empregado,
    obter_lista_projetos_empregado,
    obter_medicao_empregado,
    obter_medicoes_furo_empregado,
    obter_empregados_pendentes,
    obter_empregado_admin_por_pk,
    obter_empregado_pendente_admin_por_pk,
    obter_ficheiro_empregado_admin,
    obter_ligacao_projeto_empregado_admin,
    obter_lista_empregados,
    obter_projeto_empregado,
    obter_levantamentos_furo_empresa,
    obter_levantamentos_furo_empregado,
    obter_devolucoes_furo_empresa,
    obter_devolucoes_furo_empregado,
    obter_registos_furo_empregado,
    obter_registos_projeto_empregado,
    obter_resumo_registos_projetos_empregado,
    obter_trabalhadores_envolvidos_projeto_empregado,
    obter_contexto_materiais_disponiveis_empregado,
)
from projetos.services.empregados import (
    construir_resumo_registos_projeto_empregado,
    garantir_individual_para_user,
    processar_acao_pendente_empregado,
    processar_fluxo_apagar_empregado_admin,
    processar_fluxo_empregado_admin_form,
    processar_fluxo_ficheiro_empregado_admin_form,
    processar_fluxo_registo_empregado_form,
    processar_fluxo_remover_ficheiro_empregado,
    processar_fluxo_terminar_ligacao_projeto,
    processar_fluxo_ligacao_projeto_admin_form,
)

logger = logging.getLogger("core")


# ---------------- HELPERS ----------------
def _obter_empresa_admin_empregados(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        logger.warning(
            "Falha ao resolver empresa administrativa em empregados.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empresa, None



def _obter_empregado_autenticado(request):
    logger.debug(
        "A resolver empregado autenticado em empregados.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado, ligado_por_fallback, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
        vincular_por_email=True,
    )
    if resposta_erro:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em empregados.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro

    if ligado_por_fallback:
        logger.warning(
            "Ligação automática User -> Empregados executada em empregados.py. user_id=%s, empregado_id=%s, empresa_id=%s, email='%s'",
            request.user.id,
            empregado.id,
            empregado.empresa_id,
            getattr(request.user, "email", ""),
        )
    return empregado, None


def _resolver_empregado_por_user_ou_email(user):
    empregado, ligado_por_fallback = resolver_empregado_por_user_ou_email(user)
    if ligado_por_fallback and empregado is not None:
        logger.warning(
            "Ligação automática User -> Empregados executada em empregados.py. user_id=%s, empregado_id=%s, empresa_id=%s, email='%s'",
            user.id,
            empregado.id,
            empregado.empresa_id,
            getattr(user, "email", ""),
        )
    return empregado


def _resolver_individual_por_user(user):
    return obter_individual_por_user(user)


def _success_redirect(request, mensagem, destino):
    messages.success(request, mensagem)
    return redirect(destino)


def _require_post_or_redirect(request, destino):
    if request.method != "POST":
        return redirect(destino)
    return None


# ---------------- EMPREGADOS ----------------
# TODO futuro:
# - quando o fluxo multiempresa estiver fechado, associar o registo inicial a uma empresa/contexto controlado
# - validar convites ou código da empresa no onboarding, se essa regra for adotada
def registo_empregado(request):
    logger.info(
        "Entrada na view registo_empregado. method=%s, authenticated=%s",
        request.method,
        request.user.is_authenticated,
    )
    fluxo = processar_fluxo_registo_empregado_form(
        method=request.method,
        post_data=request.POST,
        form_class=EmpregadoRegistroForm,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["estado"] == "ok":
            logger.info("Formulário de registo de empregado válido. email='%s'", form.cleaned_data.get("email"))
            resultado_registo = resultado["resultado_registo"]
            if resultado_registo == "individual":
                messages.success(
                    request,
                    "Conta individual criada com sucesso. Já podes entrar na área de trabalhador.",
                )
            else:
                messages.success(
                    request,
                    "Registo enviado com sucesso. Aguarde aprovação da empresa para receber acesso à plataforma.",
                )
            return redirect("login")
        messages.error(request, "Existem erros no formulário. Corrija os campos assinalados.")
        logger.warning("Erros no formulário de registo de empregado: %s", form.errors)

    logger.info("Render da view registo_empregado concluído.")
    return render(request, "projetos/registo_empregado.html", {
        "form": form,
        "titulo": "Registo de Empregado",
    })


@login_required
@admin_required
def empregado_list(request):
    logger.info(
        "Entrada na view empregado_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_list. user_id=%s", request.user.id)
        return resposta_erro

    empregados = obter_lista_empregados(empresa=empresa)
    logger.info(
        "View empregado_list carregada com sucesso. user_id=%s, empresa_id=%s, total_empregados=%s",
        request.user.id,
        empresa.id,
        empregados.count() if hasattr(empregados, "count") else "n/a",
    )
    return render(request, "projetos/empregado_list.html", {
        "empregados": empregados,
    })


@login_required
@admin_required
def empregado_create(request):
    logger.info(
        "Entrada na view empregado_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_create. user_id=%s", request.user.id)
        return resposta_erro

    fluxo = processar_fluxo_empregado_admin_form(
        method=request.method,
        post_data=request.POST,
        files_data=request.FILES,
        form_class=EmpregadoCreateForm,
        empresa=empresa,
        acao="create",
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["ok"]:
            user = resultado["user"]
            empregado = resultado["empregado"]
            logger.info(
                "Ligação criada em empregado_create. user_id=%s, empregado_id=%s, empregado_user_id=%s, empresa_id=%s",
                user.id,
                empregado.id,
                empregado.user_id,
                empregado.empresa_id,
            )
            logger.info(
                "Empregado criado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, novo_username='%s'",
                request.user.id,
                empresa.id,
                empregado.id,
                user.username,
            )
            messages.success(
                request,
                f"Empregado criado com sucesso. Utilizador: {user.username}",
            )
            messages.info(
                request,
                "O novo empregado ficou pendente. Aprova o registo para lhe dar acesso à plataforma.",
            )
            return redirect(empregado)

        if resultado.get("erro_tecnico") is not None:
            logger.exception(
                "Erro ao criar empregado com utilizador. admin_user_id=%s, empresa_id=%s, erro=%s",
                request.user.id,
                empresa.id,
                resultado["erro_tecnico"],
            )
            messages.error(request, "Erro ao criar empregado. Verifique os dados e tente novamente.")
        else:
            logger.warning(
                "Formulário inválido em empregado_create. user_id=%s, erros=%s",
                request.user.id,
                resultado.get("erros_form"),
            )
            messages.error(request, resultado["mensagem_erro"])

    return render(request, "projetos/empregado_form.html", {
        "form": form,
        "titulo": "Novo Empregado",
    })


@login_required
@admin_required
def empregado_detail_legacy(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_detail_legacy. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_admin_por_pk(pk, empresa)
    return redirect(empregado)


@login_required
@admin_required
def empregado_detail(request, pk, slug):
    logger.info(
        "Entrada na view empregado_detail. user_id=%s, username='%s', empregado_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_detail. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_pendente_admin_por_pk(pk, empresa)
    if slug != empregado.slug_url:
        return redirect(empregado)

    logger.info(
        "View empregado_detail carregada com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s",
        request.user.id,
        empresa.id,
        empregado.id,
    )
    return render(request, "projetos/empregado_detail.html", {
        "empregado": empregado,
        "page_title": f"Empregado · {empregado.nome}",
    })


@login_required
@admin_required
def empregado_update(request, pk):
    logger.info(
        "Entrada na view empregado_update. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_update. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_admin_por_pk(pk, empresa)

    fluxo = processar_fluxo_empregado_admin_form(
        method=request.method,
        post_data=request.POST,
        files_data=request.FILES,
        form_class=EmpregadoUpdateForm,
        empresa=empresa,
        acao="update",
        instance=empregado,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["ok"]:
            empregado = resultado["empregado"]
            logger.info(
                "Empregado atualizado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s",
                request.user.id,
                empresa.id,
                empregado.id,
            )
            messages.success(request, "Empregado atualizado com sucesso.")
            return redirect(empregado)

        if resultado.get("erro_tecnico") is not None:
            logger.exception(
                "Erro técnico ao atualizar empregado. user_id=%s, empregado_pk=%s, erro=%s",
                request.user.id,
                pk,
                resultado["erro_tecnico"],
            )
            messages.error(request, "Erro ao atualizar empregado. Verifique os dados.")
        else:
            logger.warning(
                "Erro ao atualizar empregado. user_id=%s, empregado_pk=%s, erros=%s",
                request.user.id,
                pk,
                resultado.get("erros_form"),
            )
            messages.error(request, resultado["mensagem_erro"])
    return render(request, "projetos/empregado_form.html", {
        "form": form,
        "titulo": "Editar Empregado",
        "empregado": empregado,
    })


@login_required
@admin_required
def empregado_delete(request, pk):
    logger.info(
        "Entrada na view empregado_delete. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_delete. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_admin_por_pk(pk, empresa)

    resultado = processar_fluxo_apagar_empregado_admin(
        method=request.method,
        empregado=empregado,
        empresa=empresa,
    )

    if resultado["ok"]:
        logger.info(
            "Empregado apagado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s",
            request.user.id,
            empresa.id,
            resultado["empregado_id"],
        )
        messages.success(request, "Empregado apagado com sucesso.")
        return redirect(reverse("projetos:empregado_list"))

    return render(request, "projetos/empregado_confirm_delete.html", {
        "empregado": empregado,
    })


@login_required
@admin_required
def empregado_adicionar_projeto(request, pk):
    logger.info(
        "Entrada na view empregado_adicionar_projeto. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_adicionar_projeto. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_admin_por_pk(pk, empresa)

    fluxo = processar_fluxo_ligacao_projeto_admin_form(
        method=request.method,
        post_data=request.POST,
        form_class=EmpregadoProjetoForm,
        empresa=empresa,
        empregado=empregado,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["ok"]:
            ligacao = resultado["ligacao"]
            logger.info(
                "Projeto associado ao empregado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, ligacao_id=%s",
                request.user.id,
                empresa.id,
                empregado.id,
                ligacao.id,
            )
            messages.success(request, "Projeto associado ao empregado com sucesso.")
            return redirect(empregado)
        if resultado["erro"] == "validacao":
            logger.warning(
                "Tentativa inválida em empregado_adicionar_projeto. user_id=%s, empregado_id=%s",
                request.user.id,
                empregado.id,
            )
        else:
            logger.warning(
                "Erro ao associar projeto ao empregado. user_id=%s, empregado_pk=%s, erros=%s",
                request.user.id,
                pk,
                resultado.get("erros_form"),
            )
            messages.error(request, "Erro ao associar projeto. Verifique os dados.")
    return render(request, "projetos/empregado_projeto_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Associar Projeto ao Empregado",
    })


@login_required
@admin_required
def empregado_editar_projeto(request, pk, ligacao_id):
    logger.info(
        "Entrada na view empregado_editar_projeto. user_id=%s, username='%s', empregado_pk=%s, ligacao_id=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        ligacao_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_editar_projeto. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_admin_por_pk(pk, empresa)
    ligacao = obter_ligacao_projeto_empregado_admin(ligacao_id, empregado, empresa)

    fluxo = processar_fluxo_ligacao_projeto_admin_form(
        method=request.method,
        post_data=request.POST,
        form_class=EmpregadoProjetoForm,
        empresa=empresa,
        empregado=empregado,
        ligacao=ligacao,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]

    if resultado:
        if resultado["ok"]:
            nova_ligacao = resultado["ligacao"]
            logger.info(
                "Ligação projeto/empregado atualizada com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, ligacao_id=%s",
                request.user.id,
                empresa.id,
                empregado.id,
                nova_ligacao.id,
            )
            messages.success(request, "Ligação projeto/empregado atualizada com sucesso.")
            return redirect(empregado)
        if resultado["erro"] == "validacao":
            logger.warning(
                "Tentativa inválida em empregado_editar_projeto. user_id=%s, empregado_id=%s",
                request.user.id,
                empregado.id,
            )
        else:
            logger.warning(
                "Erro ao atualizar ligação projeto/empregado. user_id=%s, empregado_pk=%s, ligacao_id=%s, erros=%s",
                request.user.id,
                pk,
                ligacao_id,
                resultado.get("erros_form"),
            )
            messages.error(request, "Erro ao atualizar ligação. Verifique os dados.")
    return render(request, "projetos/empregado_projeto_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Editar Ligação de Projeto",
    })


@login_required
@admin_required
def empregado_terminar_projeto(request, pk, ligacao_id):
    logger.info(
        "Entrada na view empregado_terminar_projeto. user_id=%s, username='%s', empregado_pk=%s, ligacao_id=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        ligacao_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_terminar_projeto. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_admin_por_pk(pk, empresa)
    ligacao = obter_ligacao_projeto_empregado_admin(ligacao_id, empregado, empresa)

    resultado = processar_fluxo_terminar_ligacao_projeto(
        method=request.method,
        ligacao=ligacao,
        empresa=empresa,
    )
    if resultado["ok"]:
        logger.info(
            "Projeto encerrado para empregado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, ligacao_id=%s",
            request.user.id,
            empresa.id,
            empregado.id,
            ligacao.id,
        )
        return _success_redirect(request, "Projeto encerrado para este empregado com sucesso.", empregado)

    return render(request, "projetos/empregado_projeto_confirm_terminar.html", {
        "empregado": empregado,
        "ligacao": ligacao,
    })


@login_required
@admin_required
def empregado_adicionar_ficheiro(request, pk):
    logger.info(
        "Entrada na view empregado_adicionar_ficheiro. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_adicionar_ficheiro. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_admin_por_pk(pk, empresa)

    fluxo = processar_fluxo_ficheiro_empregado_admin_form(
        method=request.method,
        post_data=request.POST,
        files_data=request.FILES,
        form_class=EmpregadoFicheiroForm,
        empregado=empregado,
        empresa=empresa,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            ficheiro = resultado["ficheiro"]
            logger.info(
                "Ficheiro adicionado ao empregado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, ficheiro_id=%s",
                request.user.id,
                empresa.id,
                empregado.id,
                ficheiro.id,
            )
            messages.success(request, "Ficheiro adicionado com sucesso.")
            return redirect(empregado)
        else:
            logger.warning(
                "Erro ao adicionar ficheiro ao empregado. user_id=%s, empregado_pk=%s, erros=%s",
                request.user.id,
                pk,
                resultado.get("erros_form"),
            )
            messages.error(request, "Erro ao adicionar ficheiro. Verifique os dados.")

    return render(request, "projetos/empregado_ficheiro_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Adicionar Ficheiro ao Empregado",
    })


@login_required
@admin_required
def empregado_apagar_ficheiro(request, pk, ficheiro_id):
    logger.info(
        "Entrada na view empregado_apagar_ficheiro. user_id=%s, username='%s', empregado_pk=%s, ficheiro_id=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        ficheiro_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_apagar_ficheiro. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_admin_por_pk(pk, empresa)
    ficheiro = obter_ficheiro_empregado_admin(ficheiro_id, empregado, empresa)

    resultado = processar_fluxo_remover_ficheiro_empregado(
        method=request.method,
        ficheiro=ficheiro,
    )
    if resultado["ok"]:
        logger.info(
            "Ficheiro removido do empregado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, ficheiro_id=%s",
            request.user.id,
            empresa.id,
            empregado.id,
            resultado["ficheiro_id"],
        )
        messages.success(request, "Ficheiro removido com sucesso.")
        return redirect(empregado)

    return render(request, "projetos/empregado_ficheiro_confirm_delete.html", {
        "empregado": empregado,
        "ficheiro": ficheiro,
    })


@login_required
@admin_required
def empregado_pendentes(request):
    logger.info(
        "Entrada na view empregado_pendentes. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_pendentes. user_id=%s", request.user.id)
        return resposta_erro

    empregados = obter_empregados_pendentes(empresa=empresa)
    logger.info(
        "View empregado_pendentes carregada com sucesso. user_id=%s, empresa_id=%s, total_pendentes=%s",
        request.user.id,
        empresa.id,
        empregados.count() if hasattr(empregados, "count") else "n/a",
    )
    return render(request, "projetos/empregado_pendentes.html", {
        "empregados": empregados,
        "titulo": "Empregados Pendentes de Aprovação",
    })


@login_required
@admin_required
def empregado_aprovar(request, pk):
    logger.info(
        "Entrada na view empregado_aprovar. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_aprovar. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_admin_por_pk(pk, empresa)

    bloqueio_post = _require_post_or_redirect(request, "projetos:empregado_pendentes")
    if bloqueio_post:
        if request.method == "GET":
            return render(request, "projetos/empregado_aprovar_confirm.html", {"empregado": empregado})
        return bloqueio_post

    processar_acao_pendente_empregado(acao="aprovar", empregado=empregado, empresa=empresa)
    logger.info(
        "Empregado aprovado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s",
        request.user.id,
        empresa.id,
        empregado.id,
    )
    return _success_redirect(request, "Empregado aprovado com sucesso.", reverse("projetos:empregado_pendentes"))


@login_required
@admin_required
def empregado_rejeitar(request, pk):
    logger.info(
        "Entrada na view empregado_rejeitar. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_rejeitar. user_id=%s", request.user.id)
        return resposta_erro

    empregado = obter_empregado_pendente_admin_por_pk(pk, empresa)

    bloqueio_post = _require_post_or_redirect(request, "projetos:empregado_pendentes")
    if bloqueio_post:
        return bloqueio_post

    resultado = processar_acao_pendente_empregado(acao="rejeitar", empregado=empregado, empresa=empresa)["resultado"]
    logger.info(
        "Empregado pendente rejeitado/removido com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, empregado_nome='%s'",
        request.user.id,
        empresa.id,
        resultado["empregado_id"],
        resultado["empregado_nome"],
    )
    return _success_redirect(request, "Registo do empregado rejeitado com sucesso.", "projetos:empregado_pendentes")


@login_required
@empregado_required
def meus_furos_empregado(request):
    logger.info(
        "Entrada na view meus_furos_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view meus_furos_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furos = obter_lista_furos_empregado(empregado)

    logger.info(
        "View meus_furos_empregado carregada com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s, total_furos=%s",
        request.user.id,
        empregado.id,
        empregado.empresa_id,
        furos.count(),
    )
    return render(request, "projetos/meus_furos_empregado.html", {
        "empregado": empregado,
        "furos": furos,
        "titulo": "Meus Furos",
    })

@login_required
@empregado_required
def furo_detail_empregado(request, pk):
    logger.info(
        "Entrada na view furo_detail_empregado. user_id=%s, username='%s', furo_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_detail_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furo = obter_furo_empregado(pk=pk, empregado=empregado)
    if not furo or not empregado_tem_acesso_furo(empregado, furo):
        logger.warning(
            "Empregado sem permissão para furo_detail_empregado. user_id=%s, empregado_id=%s, furo_id=%s",
            request.user.id,
            empregado.id,
            furo.id,
        )
        messages.error(request, "Não tens permissão para ver os detalhes deste furo.")
        return redirect("projetos:meus_furos_empregado")

    medicoes = obter_medicoes_furo_empregado(empregado, furo)
    registos = obter_registos_furo_empregado(empregado, furo)
    levantamentos = obter_levantamentos_furo_empregado(empregado, furo)
    levantamentos_furo = obter_levantamentos_furo_empresa(empregado, furo)
    devolucoes = obter_devolucoes_furo_empregado(empregado, furo)
    devolucoes_furo = obter_devolucoes_furo_empresa(empregado, furo)

    logger.info(
        "View furo_detail_empregado carregada com sucesso. user_id=%s, empregado_id=%s, furo_id=%s",
        request.user.id,
        empregado.id,
        furo.id,
    )
    return render(request, "projetos/furo_detail_empregado.html", {
        "empregado": empregado,
        "furo": furo,
        "medicoes": medicoes,
        "registos": registos,
        "levantamentos": levantamentos,
        "levantamentos_furo": levantamentos_furo,
        "devolucoes": devolucoes,
        "devolucoes_furo": devolucoes_furo,
    })

@login_required
@empregado_required
def furo_3d_empregado(request, pk):
    logger.info(
        "Entrada na view furo_3d_empregado. user_id=%s, username='%s', furo_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_3d_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furo = obter_furo_empregado(pk=pk, empregado=empregado)
    if not furo or not empregado_tem_acesso_furo(empregado, furo):
        logger.warning(
            "Empregado sem permissão para furo_3d_empregado. user_id=%s, empregado_id=%s, furo_id=%s",
            request.user.id,
            empregado.id,
            furo.id,
        )
        messages.error(request, "Não tens permissão para ver o 3D deste furo.")
        return redirect("projetos:meus_furos_empregado")

    logger.info(
        "A redirecionar furo_3d_empregado para rota canónica. user_id=%s, empregado_id=%s, furo_id=%s",
        request.user.id,
        empregado.id,
        furo.id,
    )
    return redirect("projetos:furo_3d_detail", pk=furo.pk, slug=furo.slug_url)


@login_required
@empregado_required
def medicao_list_empregado(request):
    logger.info(
        "Entrada na view medicao_list_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view medicao_list_empregado. user_id=%s", request.user.id)
        return resposta_erro

    medicoes = obter_lista_medicoes_empregado(empregado)

    logger.info(
        "View medicao_list_empregado carregada com sucesso. user_id=%s, empregado_id=%s, total_medicoes=%s",
        request.user.id,
        empregado.id,
        medicoes.count(),
    )
    return render(request, "projetos/medicao_empregado_list.html", {
        "empregado": empregado,
        "medicoes": medicoes,
        "titulo": "Minhas Medições",
    })


@login_required
@empregado_required
def medicao_detail_empregado(request, pk):
    logger.info(
        "Entrada na view medicao_detail_empregado. user_id=%s, username='%s', medicao_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view medicao_detail_empregado. user_id=%s", request.user.id)
        return resposta_erro

    medicao = obter_medicao_empregado(pk=pk, empregado=empregado)
    if not medicao or not empregado_tem_acesso_furo(empregado, medicao.furo):
        logger.warning(
            "Empregado sem permissão para medicao_detail_empregado. user_id=%s, empregado_id=%s, medicao_id=%s, furo_id=%s",
            request.user.id,
            empregado.id,
            medicao.id,
            medicao.furo_id,
        )
        messages.error(request, "Não tens permissão para ver esta medição.")
        return redirect("projetos:medicao_list_empregado")

    logger.info(
        "View medicao_detail_empregado carregada com sucesso. user_id=%s, empregado_id=%s, medicao_id=%s",
        request.user.id,
        empregado.id,
        medicao.id,
    )
    return render(request, "projetos/medicao_empregado_detail.html", {
        "empregado": empregado,
        "medicao": medicao,
        "furo": medicao.furo,
        "titulo": "Detalhe da Medição",
    })

# -------  MEUS PROJETOS ------------- #
@login_required
@empregado_required
def meus_projetos_empregado(request):
    logger.info(
        "Entrada na view meus_projetos_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view meus_projetos_empregado. user_id=%s", request.user.id)
        return resposta_erro

    projetos = obter_lista_projetos_empregado(empregado)
    resumo_por_projeto = obter_resumo_registos_projetos_empregado(empregado, projetos)

    logger.info(
        "View meus_projetos_empregado carregada com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s, total_projetos=%s",
        request.user.id,
        empregado.id,
        empregado.empresa_id,
        projetos.count(),
    )
    return render(request, "projetos/meus_projetos_empregado.html", {
        "empregado": empregado,
        "projetos": projetos,
        "resumo_por_projeto": resumo_por_projeto,
        "titulo": "Meus Projetos",
    })

@login_required
@empregado_required
def projeto_detail_empregado(request, pk):
    logger.info(
        "Entrada na view projeto_detail_empregado. user_id=%s, username='%s', projeto_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_detail_empregado. user_id=%s", request.user.id)
        return resposta_erro

    projeto = obter_projeto_empregado(pk=pk, empregado=empregado)
    if not projeto or not empregado_tem_acesso_projeto(empregado, projeto):
        logger.warning(
            "Empregado sem permissão para projeto_detail_empregado. user_id=%s, empregado_id=%s, projeto_id=%s",
            request.user.id,
            empregado.id,
            projeto.id,
        )
        messages.error(request, "Não tens permissão para ver este projeto.")
        return redirect("projetos:meus_projetos_empregado")

    furos = obter_furos_projeto_empregado(empregado, projeto)
    trabalhadores_envolvidos = obter_trabalhadores_envolvidos_projeto_empregado(empregado, projeto)

    registos = obter_registos_projeto_empregado(empregado, projeto)
    resumo_registos = construir_resumo_registos_projeto_empregado(registos=registos)

    logger.info(
        "View projeto_detail_empregado carregada com sucesso. user_id=%s, empregado_id=%s, projeto_id=%s",
        request.user.id,
        empregado.id,
        projeto.id,
    )
    return render(request, "projetos/projeto_detail_empregado.html", {
        "empregado": empregado,
        "projeto": projeto,
        "furos": furos,
        "trabalhadores_envolvidos": trabalhadores_envolvidos,
        **resumo_registos,
    })

@login_required
@empregado_required
def area_empregado(request):
    logger.info(
        "Entrada na view area_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    perfil = obter_perfil_ativo_por_user(request.user)
    if perfil and perfil.tipo_acesso == "individual":
        individual, foi_criado = garantir_individual_para_user(request.user)
        if foi_criado:
            messages.info(
                request,
                "A tua conta individual foi reparada automaticamente. Já podes continuar.",
            )

        return render(request, "projetos/area_individual.html", {
            "individual": individual,
            "horas_total": individual.total_horas or 0,
            "metros_total": individual.total_metros or 0,
            "total_registos": individual.total_registos or 0,
        })

    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view area_empregado. user_id=%s", request.user.id)
        return resposta_erro

    contexto_empregado = obter_contexto_area_empregado(empregado, empresa=empregado.empresa)
    contexto_empregado["configuracoes_perfuracao"] = obter_lista_configuracoes_perfuracao_empregado(
        empregado,
        empresa=empregado.empresa,
    )

    logger.info(
        "View area_empregado carregada com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s",
        request.user.id,
        empregado.id,
        empregado.empresa_id,
    )
    return render(request, "projetos/area_empregado.html", contexto_empregado)

# --------- REDIRECT ------------

def redirect_after_login(request):
    logger.info(
        "Entrada na view redirect_after_login. authenticated=%s, user_id=%s",
        request.user.is_authenticated,
        getattr(request.user, "id", None),
    )

    if not request.user.is_authenticated:
        logger.warning("redirect_after_login chamado sem utilizador autenticado.")
        return redirect("login")

    if request.user.is_superuser:
        logger.info(
            "Acesso total via superuser em redirect_after_login. user_id=%s",
            request.user.id,
        )
        return redirect("plataforma:dashboard")

    perfil = obter_perfil_ativo_por_user(request.user)

    if perfil:
        logger.info(
            "PerfilPlataforma encontrado em redirect_after_login. user_id=%s, tipo_acesso=%s, empresa_id=%s",
            request.user.id,
            perfil.tipo_acesso,
            perfil.empresa_id,
        )

        if perfil.tipo_acesso in ["platform_owner", "platform_admin"]:
            return redirect("plataforma:dashboard")

        if perfil.tipo_acesso in ["empresa_admin", "empresa_gestor"]:
            return redirect(reverse("projetos:dashboard"))

        if perfil.tipo_acesso in ["empregado", "individual"]:
            return redirect(reverse("projetos:area_empregado"))

    empregado = _resolver_empregado_por_user_ou_email(request.user)
    if empregado:
        logger.info(
            "Empregado encontrado em redirect_after_login. user_id=%s, empregado_id=%s, aprovado=%s, empresa_id=%s",
            request.user.id,
            empregado.id,
            empregado.aprovado,
            empregado.empresa_id,
        )

        if not empregado.aprovado:
            logger.warning(
                "Empregado encontrado mas não aprovado em redirect_after_login. user_id=%s, empregado_id=%s",
                request.user.id,
                empregado.id,
            )

        if not empregado.empresa_id:
            logger.warning(
                "Empregado encontrado mas sem empresa em redirect_after_login. user_id=%s, empregado_id=%s",
                request.user.id,
                empregado.id,
            )
    else:
        logger.warning(
            "Nenhum Empregados ligado ao utilizador em redirect_after_login. user_id=%s, email='%s'",
            request.user.id,
            getattr(request.user, "email", ""),
        )

    if empregado and empregado.aprovado and empregado.empresa_id:
        logger.info(
            "Fallback via Empregados em redirect_after_login. user_id=%s, empregado_id=%s, empresa_id=%s",
            request.user.id,
            empregado.id,
            empregado.empresa_id,
        )
        return redirect(reverse("projetos:area_empregado"))

    individual = _resolver_individual_por_user(request.user)
    if individual:
        logger.info(
            "Fallback via Individual em redirect_after_login. user_id=%s, individual_id=%s",
            request.user.id,
            individual.id,
        )
        return redirect(reverse("projetos:area_empregado"))

    logger.warning(
        "Conta sem contexto válido em redirect_after_login. user_id=%s",
        request.user.id,
    )
    messages.error(
        request,
        "A tua conta não está configurada corretamente. Contacta o administrador.",
    )
    return redirect("website:home")


def redirect_view(request):
    return redirect_after_login(request)


# ------ MATERIAIS EMPREGADO ------- # 
@login_required
@empregado_required
def materiais_disponiveis_empregado(request):
    logger.info(
        "Entrada na view materiais_disponiveis_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view materiais_disponiveis_empregado. user_id=%s", request.user.id)
        return resposta_erro
    perfil = obter_perfil_ativo_por_user(request.user)
    conta_individual = bool(perfil and perfil.tipo_acesso == "individual")

    projeto_id = request.GET.get("projeto")
    furo_id = request.GET.get("furo")
    nome = (request.GET.get("nome") or "").strip()

    contexto_materiais = obter_contexto_materiais_disponiveis_empregado(
        empregado,
        projeto_id=projeto_id or "",
        furo_id=furo_id or "",
        nome=nome,
        incluir_todos_empresa=conta_individual,
    )
    materiais = contexto_materiais["materiais"]
    projetos = contexto_materiais["projetos"]
    furos = contexto_materiais["furos"]

    logger.info(
        "View materiais_disponiveis_empregado carregada com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s, total_materiais=%s, filtro_nome='%s'",
        request.user.id,
        empregado.id,
        empregado.empresa_id,
        materiais.count(),
        nome,
    )
    return render(request, "projetos/materiais_disponiveis_empregado.html", {
        "empregado": empregado,
        "materiais": materiais,
        "projetos": projetos,
        "furos": furos,
        "filtros": {
            "projeto": projeto_id or "",
            "furo": furo_id or "",
            "nome": nome,
        },
        "titulo": "Materiais Disponíveis",
        "conta_individual": conta_individual,
    })
