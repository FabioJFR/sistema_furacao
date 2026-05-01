import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from core.permissions import user_is_empresa_admin
from core.permissions import user_is_global_admin
from ..decorators import admin_required, empregado_required
from projetos.selectors.furos import (
    empregado_trabalhou_no_furo,
    obter_furo,
    obter_lista_furos,
)
from projetos.services.furo_3d_io import (
    exportar_furo_3d_response,
    parse_imported_3d_file as parse_imported_3d_file_service,
)
from projetos.services.furo_3d_chart import construir_contexto_furo_3d
from projetos.services.furo_fluxos import (
    construir_contexto_furo_detail,
    construir_contexto_furo_detail_empregado,
    processar_delete_furo,
    processar_fluxo_form_furo_create,
    processar_fluxo_form_furo_update,
    processar_importacao_3d_externa,
    resolver_furo_para_3d,
    listar_furos_para_utilizador,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.acesso_contexto import obter_empregado_autenticado_contexto
from projetos.services.acesso_contexto import obter_empresa_contexto_gestao_furos
from projetos.services.furos import (
    processar_acao_reativar_furo,
    processar_acao_terminar_furo,
)

logger = logging.getLogger("core")


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def _parse_imported_3d_file(uploaded_file):
    return parse_imported_3d_file_service(uploaded_file)


def _obter_empresa_admin_furos(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        logger.warning(
            "Falha ao resolver empresa administrativa em furos.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empresa, None



def _obter_empregado_autenticado_furos(request):
    logger.debug(
        "A resolver empregado autenticado em furos.py. user_id=%s, username='%s'",
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
            "Utilizador autenticado sem registo em Empregados em furos.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro

    return empregado, None


def _obter_empresa_contexto_gestao_furos(request):
    return obter_empresa_contexto_gestao_furos(request=request)



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

    furo = obter_furo(pk, empresa=empregado.empresa_id)
    trabalhou_no_furo = empregado_trabalhou_no_furo(empregado, furo)
    if not trabalhou_no_furo:
        logger.warning(
            "Empregado sem permissão para furo_detail_empregado em furos.py. user_id=%s, empregado_id=%s, furo_id=%s",
            request.user.id,
            empregado.id,
            furo.id,
        )
        messages.error(request, "Não tens permissão para ver os detalhes deste furo.")
        return redirect("projetos:area_empregado")

    contexto_detail = construir_contexto_furo_detail_empregado(
        empregado=empregado,
        furo=furo,
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
        **contexto_detail,
    })



@login_required
def furo_create(request):
    logger.info(
        "Entrada na view furo_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_create. user_id=%s", request.user.id)
        return resposta_erro

    empregado_contexto = None
    if not user_is_empresa_admin(request.user):
        empregado_contexto, resposta_empregado = _obter_empregado_autenticado_furos(request)
        if resposta_empregado:
            logger.warning("Acesso bloqueado por contexto de empregado na view furo_create. user_id=%s", request.user.id)
            return resposta_empregado

    fluxo = processar_fluxo_form_furo_create(
        request_method=request.method,
        request_post=request.POST,
        empresa_id=empresa_id,
        empregado_contexto=empregado_contexto,
    )
    form = fluxo["form"]
    memoria_zona_alerta = fluxo["memoria_zona_alerta"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            furo = resultado["furo"]
            logger.info(
                "Furo criado com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
                request.user.id,
                empresa.id,
                furo.pk,
            )
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect(furo)

        logger.warning(
            "Erro ao criar furo. user_id=%s, erros=%s",
            request.user.id,
            resultado["erros_form"],
        )
        messages.error(request, resultado["mensagem_erro"])

    return render(request, "projetos/form.html", {
        "form": form,
        "titulo": "Criar Novo Furo",
        "memoria_zona_alerta": memoria_zona_alerta,
    })


@login_required
def furo_detail_legacy(request, pk):
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        return resposta_erro

    furo = obter_furo(pk, empresa=empresa_id)
    return redirect(furo)


@login_required
def furo_detail(request, pk, slug):
    logger.info(
        "Entrada na view furo_detail. user_id=%s, username='%s', furo_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_detail. user_id=%s", request.user.id)
        return resposta_erro

    context = construir_contexto_furo_detail(pk=pk, empresa_id=empresa_id)
    furo = context["furo"]
    if slug != furo.slug_url:
        return redirect(furo)

    logger.info(
        "View furo_detail carregada com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
        request.user.id,
        empresa.id,
        furo.pk,
    )
    return render(request, "projetos/furo_detail.html", context)


@login_required
def furo_terminar(request, pk):
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        return resposta_erro

    furo = obter_furo(pk, empresa=empresa_id)
    resultado = processar_acao_terminar_furo(
        request_method=request.method,
        furo=furo,
        empresa=empresa_id,
        terminado_por=request.user,
    )
    if resultado["deve_redirecionar_legacy"]:
        return redirect("projetos:furo_detail_legacy", pk=pk)
    if resultado["mensagem_sucesso"]:
        messages.success(request, resultado["mensagem_sucesso"])
    return redirect(resultado["furo"])


@login_required
def furo_reativar(request, pk):
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        return resposta_erro

    furo = obter_furo(pk, empresa=empresa_id)
    resultado = processar_acao_reativar_furo(
        request_method=request.method,
        furo=furo,
        empresa=empresa_id,
    )
    if resultado["deve_redirecionar_legacy"]:
        return redirect("projetos:furo_detail_legacy", pk=pk)
    if resultado["mensagem_sucesso"]:
        messages.success(request, resultado["mensagem_sucesso"])
    return redirect(resultado["furo"])

# Multiempresa: o administrador só pode listar e gerir furos da sua própria empresa.
@login_required
def furo_list(request):
    logger.info(
        "Entrada na view furo_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_list. user_id=%s", request.user.id)
        return resposta_erro

    is_admin = user_is_empresa_admin(request.user)
    if not is_admin:
        empregado_contexto, resposta_empregado = _obter_empregado_autenticado_furos(request)
        if resposta_empregado:
            logger.warning("Acesso bloqueado por contexto de empregado na view furo_list. user_id=%s", request.user.id)
            return resposta_empregado

    furos = listar_furos_para_utilizador(
        empresa_id=empresa_id,
        empregado_contexto=empregado_contexto if not is_admin else None,
        is_admin=is_admin,
    )
    logger.info(
        "View furo_list carregada com sucesso. user_id=%s, empresa_id=%s, total_furos=%s",
        request.user.id,
        empresa.id,
        furos.count() if hasattr(furos, "count") else "n/a",
    )
    return render(request, "projetos/furo_list.html", {"furos": furos})




@login_required
def furo_update(request, pk):
    logger.info(
        "Entrada na view furo_update. user_id=%s, username='%s', furo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_update. user_id=%s", request.user.id)
        return resposta_erro

    fluxo = processar_fluxo_form_furo_update(
        request_method=request.method,
        request_post=request.POST,
        pk=pk,
        empresa_id=empresa_id,
    )
    form = fluxo["form"]
    furo = fluxo["furo"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:

            logger.info(
                "Furo atualizado com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
                request.user.id,
                empresa.id,
                furo.pk,
            )
            messages.success(request, resultado["mensagem_sucesso"])
            return redirect(furo)

        logger.warning(
            "Erro ao atualizar furo. user_id=%s, furo_pk=%s, erros=%s",
            request.user.id,
            pk,
            resultado["erros_form"],
        )
        messages.error(request, resultado["mensagem_erro"])

    return render(request, "projetos/furo_update.html", {
        "form": form,
        "furo": furo,
    })



@login_required
def furo_delete(request, pk):
    logger.info(
        "Entrada na view furo_delete. user_id=%s, username='%s', furo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_delete. user_id=%s", request.user.id)
        return resposta_erro

    furo = obter_furo(pk, empresa=empresa_id)
    if request.method == "POST":
        resultado = processar_delete_furo(pk=pk, empresa_id=empresa_id)
        furo_id = resultado["furo_id"]
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
def furo_3d_geologico(request, furo_id=None, pk=None, slug=None):
    furo_id = furo_id or pk
    logger.info(
        "Entrada na view furo_3d_geologico. user_id=%s, username='%s', furo_id=%s",
        request.user.id,
        request.user.username,
        furo_id,
    )
    acesso = resolver_furo_para_3d(
        request=request,
        furo_id=furo_id,
        user_is_global_admin_fn=user_is_global_admin,
        user_is_empresa_admin_fn=user_is_empresa_admin,
        obter_empresa_contexto_fn=_obter_empresa_contexto_gestao_furos,
        resolver_empresa_id_fn=_resolver_empresa_id,
        obter_empregado_contexto_fn=_obter_empregado_autenticado_furos,
    )
    if acesso["erro"]:
        logger.warning("Acesso bloqueado na view furo_3d_geologico. user_id=%s", request.user.id)
        return acesso["erro"]
    if acesso["sem_permissao"]:
        logger.warning("Empregado sem permissão para furo_3d_geologico. user_id=%s, furo_id=%s", request.user.id, furo_id)
        messages.error(request, "Não tens permissão para ver o 3D deste furo.")
        return redirect("projetos:area_empregado")
    furo = acesso["furo"]

    contexto_3d = construir_contexto_furo_3d(furo)
    if contexto_3d.get("sem_medicoes"):
        logger.info(
            "Furo sem medições em furo_3d_geologico. user_id=%s, furo_id=%s",
            request.user.id,
            furo.id,
        )
        messages.warning(request, "Este furo ainda não possui medições.")

    logger.info(
        "View furo_3d_geologico carregada com sucesso. user_id=%s, furo_id=%s, numero_medicoes=%s, estado_max=%s",
        request.user.id,
        furo.id,
        contexto_3d.get("numero_medicoes", 0),
        contexto_3d.get("estado_max", "OK"),
    )
    contexto_3d.pop("sem_medicoes", None)
    return render(request, "projetos/furo_3d.html", {"furo": furo, **contexto_3d})


@login_required
@admin_required
def furo_3d_importar_externo(request):
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    if resposta_erro:
        return resposta_erro

    resultado_importacao = {
        "imported_trace": None,
        "trace_name": "",
        "total_pontos": 0,
        "origem_aplicacao": "",
        "furo_destino_id": "",
        "observacoes": "",
        "mensagem_sucesso": None,
        "mensagem_erro": None,
    }
    if request.method == "POST":
        resultado_importacao = processar_importacao_3d_externa(
            request_post=request.POST,
            request_files=request.FILES,
            empresa=empresa,
            parse_imported_file_fn=_parse_imported_3d_file,
        )
        if resultado_importacao["mensagem_sucesso"]:
            messages.success(request, resultado_importacao["mensagem_sucesso"])
        if resultado_importacao["mensagem_erro"]:
            messages.error(request, resultado_importacao["mensagem_erro"])

    return render(
        request,
        "projetos/furo_3d_importar_externo.html",
        {
            "empresa": empresa,
            "imported_trace": resultado_importacao["imported_trace"],
            "trace_name": resultado_importacao["trace_name"],
            "total_pontos": resultado_importacao["total_pontos"],
            "furos_empresa": obter_lista_furos(empresa=empresa),
            "origem_aplicacao": resultado_importacao["origem_aplicacao"],
            "furo_destino_id": resultado_importacao["furo_destino_id"],
            "observacoes": resultado_importacao["observacoes"],
        },
    )


@login_required
def furo_3d_export(request, furo_id, formato):
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        return resposta_erro

    furo = obter_furo(furo_id, empresa=empresa_id)
    return exportar_furo_3d_response(furo, formato)
