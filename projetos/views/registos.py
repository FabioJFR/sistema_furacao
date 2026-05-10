import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from core.permissions import admin_required
from ..decorators import empregado_required

from projetos.forms.registo import (
    RegistoDiarioEmpregadoAdminForm,
    RegistoDiarioEmpregadoForm,
    RelatorioTurnoForm,
)
from projetos.selectors.registos import (
    obter_contexto_filtros_registos_admin,
    obter_relatorio_turno_admin,
    obter_relatorios_turno_admin_filtrados,
    obter_relatorios_turno_empregado,
    obter_relatorio_turno_empregado,
    obter_registo_admin,
    obter_registo_empregado,
    obter_registos_admin_filtrados,
    obter_registos_empregado,
)
from projetos.services.registos import (
    exportar_relatorios_turno_csv_bytes,
    exportar_relatorios_turno_pdf_consolidado,
    exportar_relatorio_turno_pdf,
    exportar_relatorios_turno_zip,
    exportar_relatorios_turno_xlsx_bytes,
    guardar_relatorio_turno_dedicado,
    obter_dashboard_relatorios_turno,
    obter_relatorio_turno_contexto,
    processar_fluxo_form_registo_admin,
    processar_fluxo_form_registo_empregado,
)
from projetos.services.acesso_contexto import (
    obter_empregado_autenticado_contexto,
    obter_empresa_admin_contexto,
)

logger = logging.getLogger("core")


def _resolver_registo_relatorio(relatorio):
    return getattr(relatorio, "registo", relatorio)


# -------- REGISTOS --------------


# ---------------- HELPERS ----------------
def _obter_empresa_admin_registos(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        logger.warning(
            "Falha ao resolver empresa administrativa em registos.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empresa, None



def _obter_empregado_autenticado_registos(request):
    logger.debug(
        "A resolver empregado autenticado em registos.py. user_id=%s, username='%s'",
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
            "Utilizador autenticado sem registo em Empregados em registos.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro

    return empregado, None


def _render_registo_form_empregado(request, form, relatorio_form, empregado, titulo, registo=None):
    context = {
        "form": form,
        "relatorio_form": relatorio_form,
        "empregado": empregado,
        "titulo": titulo,
    }
    if registo is not None:
        context["registo"] = registo
    return render(request, "projetos/registo_diario_form.html", context)


def _render_relatorio_turno_detail(
    request,
    *,
    relatorio,
    voltar_url,
    editar_url,
    pdf_url,
    contexto_extra=None,
):
    contexto = obter_relatorio_turno_contexto(relatorio)
    registo = _resolver_registo_relatorio(relatorio)
    context = {
        "relatorio": relatorio,
        "registo": registo,
        "cabecalho_relatorio": contexto["cabecalho"],
        "secoes_relatorio": contexto["secoes"],
        "voltar_url": voltar_url,
        "editar_url": editar_url,
        "pdf_url": pdf_url,
    }
    if contexto_extra:
        context.update(contexto_extra)
    return render(request, "projetos/relatorio_turno_detail.html", context)


def _bloquear_exportacao_empregado(request):
    messages.error(
        request,
        "A exportação de relatórios técnicos está disponível apenas para a empresa.",
    )
    return redirect("projetos:relatorio_turno_list")


def _bloquear_edicao_relatorio_empregado(request, pk):
    messages.error(
        request,
        "A edição do relatório técnico está disponível apenas para a empresa.",
    )
    return redirect("projetos:relatorio_turno_detail", pk=pk)


def _render_relatorio_turno_form(
    request,
    *,
    relatorio_form,
    relatorio,
    titulo,
    voltar_url,
    detalhe_url,
):
    contexto = obter_relatorio_turno_contexto(relatorio)
    registo = _resolver_registo_relatorio(relatorio)
    return render(
        request,
        "projetos/relatorio_turno_form.html",
        {
            "relatorio": relatorio,
            "registo": registo,
            "relatorio_form": relatorio_form,
            "titulo": titulo,
            "cabecalho_relatorio": contexto["cabecalho"],
            "voltar_url": voltar_url,
            "detalhe_url": detalhe_url,
        },
    )


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
def relatorio_turno_list(request):
    messages.info(
        request,
        "As fichas técnicas dos teus turnos estão disponíveis dentro de 'Meus Registos'.",
    )
    return redirect("projetos:registo_diario_list")


@login_required
@empregado_required
def relatorio_turno_export_zip(request):
    return _bloquear_exportacao_empregado(request)


@login_required
@empregado_required
def relatorio_turno_export_csv(request):
    return _bloquear_exportacao_empregado(request)


@login_required
@empregado_required
def relatorio_turno_export_xlsx(request):
    return _bloquear_exportacao_empregado(request)


@login_required
@empregado_required
def relatorio_turno_export_pdf_consolidado(request):
    return _bloquear_exportacao_empregado(request)


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

    fluxo = processar_fluxo_form_registo_empregado(
        form_class=RegistoDiarioEmpregadoForm,
        relatorio_form_class=RelatorioTurnoForm,
        request=request,
        empregado=empregado,
        initial={"data": timezone.now().date()},
    )
    form = fluxo["form"]
    relatorio_form = fluxo["relatorio_form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            registo = resultado["registo"]
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
            resultado.get("erros_form"),
        )
        messages.error(request, "Erro ao guardar o registo diário. Verifique os dados.")

    return _render_registo_form_empregado(request, form, relatorio_form, empregado, "Novo Registo Diário")


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

    fluxo = processar_fluxo_form_registo_empregado(
        form_class=RegistoDiarioEmpregadoForm,
        relatorio_form_class=RelatorioTurnoForm,
        request=request,
        empregado=empregado,
        registo=registo,
    )
    form = fluxo["form"]
    relatorio_form = fluxo["relatorio_form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            registo_atualizado = resultado["registo"]
            logger.info(
                "Registo diário atualizado com sucesso por empregado. user_id=%s, empregado_id=%s, registo_id=%s",
                request.user.id,
                empregado.id,
                registo_atualizado.id,
            )
            messages.success(request, "Registo diário atualizado com sucesso.")
            return redirect("projetos:registo_diario_list")
        logger.warning(
            "Erro ao atualizar registo diário por empregado. user_id=%s, registo_pk=%s, erros=%s",
            request.user.id,
            pk,
            resultado.get("erros_form"),
        )
        messages.error(request, "Erro ao atualizar o registo diário.")

    return _render_registo_form_empregado(request, form, relatorio_form, empregado, "Editar Registo Diário", registo=registo)


@login_required
@empregado_required
def relatorio_turno_detail(request, pk):
    empregado, resposta_erro = _obter_empregado_autenticado_registos(request)
    if resposta_erro:
        return resposta_erro

    relatorio = obter_relatorio_turno_empregado(empregado, pk)
    return _render_relatorio_turno_detail(
        request,
        relatorio=relatorio,
        voltar_url="projetos:registo_diario_list",
        editar_url="projetos:registo_diario_update",
        pdf_url="projetos:relatorio_turno_pdf",
        contexto_extra={
            "pode_editar_relatorio": False,
            "pode_editar_registo": False,
            "pode_exportar": False,
        },
    )


@login_required
@empregado_required
def relatorio_turno_pdf(request, pk):
    empregado, resposta_erro = _obter_empregado_autenticado_registos(request)
    if resposta_erro:
        return resposta_erro

    obter_relatorio_turno_empregado(empregado, pk)
    return _bloquear_exportacao_empregado(request)


@login_required
@empregado_required
def relatorio_turno_update(request, pk):
    empregado, resposta_erro = _obter_empregado_autenticado_registos(request)
    if resposta_erro:
        return resposta_erro

    obter_relatorio_turno_empregado(empregado, pk)
    return _bloquear_edicao_relatorio_empregado(request, pk)


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
def relatorio_turno_admin_list(request):
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    if resposta_erro:
        return resposta_erro

    resultados = obter_relatorios_turno_admin_filtrados(empresa, filtros=request.GET)
    contexto_filtros = obter_contexto_filtros_registos_admin(empresa)
    return render(
        request,
        "projetos/relatorio_turno_list.html",
        {
            "empresa": empresa,
            "relatorios": resultados["relatorios"],
            "filtros": resultados["filtros"],
            "empregados": contexto_filtros["empregados"],
            "projetos": contexto_filtros["projetos"],
            "furos": contexto_filtros["furos"],
            "total_relatorios": resultados["totais"]["total"],
            "dashboard_relatorios": obter_dashboard_relatorios_turno(resultados["relatorios"]),
            "modo_admin": True,
            "pode_exportar": True,
            "querystring_atual": request.GET.urlencode(),
        },
    )


@login_required
@admin_required
def relatorio_turno_admin_export_zip(request):
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    if resposta_erro:
        return resposta_erro

    resultados = obter_relatorios_turno_admin_filtrados(empresa, filtros=request.GET)
    conteudo_zip, nome_zip = exportar_relatorios_turno_zip(
        resultados["relatorios"],
        nome_base=f"relatorios-tecnicos-{empresa.nome}",
    )
    response = HttpResponse(conteudo_zip, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{nome_zip}"'
    return response


@login_required
@admin_required
def relatorio_turno_admin_export_csv(request):
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    if resposta_erro:
        return resposta_erro

    resultados = obter_relatorios_turno_admin_filtrados(empresa, filtros=request.GET)
    csv_bytes = exportar_relatorios_turno_csv_bytes(resultados["relatorios"])
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="relatorios_tecnicos_turno.csv"'
    response.write(csv_bytes)
    return response


@login_required
@admin_required
def relatorio_turno_admin_export_xlsx(request):
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    if resposta_erro:
        return resposta_erro

    resultados = obter_relatorios_turno_admin_filtrados(empresa, filtros=request.GET)
    try:
        xlsx_bytes = exportar_relatorios_turno_xlsx_bytes(resultados["relatorios"])
    except Exception as exc:
        messages.error(request, str(exc))
        return redirect("projetos:relatorio_turno_admin_list")
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="relatorios_tecnicos_turno.xlsx"'
    response.write(xlsx_bytes)
    return response


@login_required
@admin_required
def relatorio_turno_admin_export_pdf_consolidado(request):
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    if resposta_erro:
        return resposta_erro

    resultados = obter_relatorios_turno_admin_filtrados(empresa, filtros=request.GET)
    try:
        pdf_bytes = exportar_relatorios_turno_pdf_consolidado(resultados["relatorios"])
    except Exception as exc:
        messages.error(request, str(exc))
        return redirect("projetos:relatorio_turno_admin_list")
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="relatorios_tecnicos_turno.pdf"'
    response.write(pdf_bytes)
    return response


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

    fluxo = processar_fluxo_form_registo_admin(
        form_class=RegistoDiarioEmpregadoAdminForm,
        relatorio_form_class=RelatorioTurnoForm,
        request=request,
        registo=registo,
        empresa=empresa,
    )
    form = fluxo["form"]
    relatorio_form = fluxo["relatorio_form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
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
            registo.pk,
            resultado.get("erros_form"),
        )
        messages.error(request, "Erro ao corrigir o registo.")

    return render(
        request,
        "projetos/registo_admin_form.html",
        {
            "form": form,
            "relatorio_form": relatorio_form,
            "registo": registo,
            "titulo": "Corrigir Registo de Produção",
        },
    )


@login_required
@admin_required
def relatorio_turno_admin_detail(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    if resposta_erro:
        return resposta_erro

    relatorio = obter_relatorio_turno_admin(empresa, pk)
    return _render_relatorio_turno_detail(
        request,
        relatorio=relatorio,
        voltar_url="projetos:registos_admin_list",
        editar_url="projetos:registo_admin_update",
        pdf_url="projetos:relatorio_turno_admin_pdf",
        contexto_extra={
            "editar_relatorio_url": "projetos:relatorio_turno_admin_update",
            "pode_editar_relatorio": True,
            "pode_editar_registo": True,
            "pode_exportar": True,
        },
    )


@login_required
@admin_required
def relatorio_turno_admin_pdf(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    if resposta_erro:
        return resposta_erro

    relatorio = obter_relatorio_turno_admin(empresa, pk)
    pdf_bytes = exportar_relatorio_turno_pdf(relatorio)
    filename = f"relatorio-turno-{relatorio.numero_relatorio or relatorio.pk}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@admin_required
def relatorio_turno_admin_update(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    if resposta_erro:
        return resposta_erro

    relatorio = obter_relatorio_turno_admin(empresa, pk)
    if request.method == "POST":
        relatorio_form = RelatorioTurnoForm(request.POST, instance=relatorio, registo=relatorio, prefix="relatorio")
        resultado = guardar_relatorio_turno_dedicado(relatorio_form=relatorio_form, registo=relatorio)
        if resultado["ok"]:
            if resultado.get("apagado"):
                messages.success(request, "O conteúdo técnico do registo foi limpo por ter ficado vazio.")
                return redirect("projetos:registos_admin_list")
            messages.success(request, "Informação técnica atualizada com sucesso.")
            return redirect("projetos:relatorio_turno_admin_detail", pk=relatorio.pk)
        messages.error(request, "Erro ao atualizar a informação técnica.")
    else:
        relatorio_form = RelatorioTurnoForm(instance=relatorio, registo=relatorio, prefix="relatorio")

    return _render_relatorio_turno_form(
        request,
        relatorio_form=relatorio_form,
        relatorio=relatorio,
        titulo="Editar Informação Técnica do Registo",
        voltar_url="projetos:relatorio_turno_admin_detail",
        detalhe_url="projetos:relatorio_turno_admin_detail",
    )
