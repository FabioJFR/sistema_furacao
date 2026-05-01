import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.text import slugify

from core.permissions import admin_required

from projetos.forms import EmpresaFinanceiraForm, PreferenciasForm, SugestaoPlataformaForm
from projetos.services.opcoes_exportacao import (
    construir_resposta_download_dataset,
    construir_resposta_download_tudo,
    construir_cards_datasets,
    obter_dataset_exportacao as obter_dataset_exportacao_service,
)
from projetos.services.opcoes import (
    construir_contexto_relatorios_exportacao,
    construir_filtros_exportacao,
    obter_empresa_admin_opcoes,
    processar_fluxo_financeiro_admin_form,
    processar_fluxo_preferencias_admin_form,
)
from projetos.services.sugestoes import processar_submissao_sugestao
from projetos.selectors.opcoes import (
    listar_furos_filtro_exportacao,
    listar_projetos_filtro_exportacao,
    obter_resultados_procurar_dashboard,
)
from projetos.selectors.preferencias import (
    garantir_preferencias_empresa,
    obter_ou_criar_preferencias_user,
)
logger = logging.getLogger("core")


def _obter_empresa_admin_or_redirect(request):
    return obter_empresa_admin_opcoes(request=request)


def _processar_form_preferencias(request, resultado):
    if not resultado["ok"]:
        messages.error(request, "Erro ao guardar preferências.")
        return None

    preferencias = resultado["preferencias"]
    if preferencias.idioma:
        translation.activate(preferencias.idioma)
        request.session["django_language"] = preferencias.idioma
    messages.success(request, "Preferências guardadas com sucesso.")
    return redirect("projetos:definicoes_admin")


def _processar_form_financeiro(request, resultado):
    if not resultado["ok"]:
        messages.error(request, "Erro ao guardar definições financeiras.")
        return None
    messages.success(request, "Definições financeiras guardadas com sucesso.")
    return redirect("projetos:definicoes_financeiras_admin")


@login_required
@admin_required
def definicoes_admin(request):
    empresa, resposta_erro = _obter_empresa_admin_or_redirect(request)
    if resposta_erro:
        return resposta_erro

    preferencias, _ = obter_ou_criar_preferencias_user(request.user)
    preferencias = garantir_preferencias_empresa(preferencias, empresa)

    fluxo = processar_fluxo_preferencias_admin_form(
        method=request.method,
        post_data=request.POST,
        form_class=PreferenciasForm,
        preferencias=preferencias,
        user=request.user,
        empresa=empresa,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta = _processar_form_preferencias(request, resultado)
        if resposta:
            return resposta

    return render(
        request,
        "projetos/definicoes_admin.html",
        {
            "form": form,
            "titulo": "Definições da Empresa",
            "empresa": empresa,
        },
    )


@login_required
@admin_required
def definicoes_financeiras_admin(request):
    empresa, resposta_erro = _obter_empresa_admin_or_redirect(request)
    if resposta_erro:
        return resposta_erro

    fluxo = processar_fluxo_financeiro_admin_form(
        method=request.method,
        post_data=request.POST,
        form_class=EmpresaFinanceiraForm,
        empresa=empresa,
    )
    financeiro_form = fluxo["financeiro_form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta = _processar_form_financeiro(request, resultado)
        if resposta:
            return resposta

    financeiro_preview = empresa.recalcular_indicadores_financeiros(guardar=False)

    return render(
        request,
        "projetos/definicoes_financeiras_admin.html",
        {
            "financeiro_form": financeiro_form,
            "titulo": "Definições Financeiras da Empresa",
            "empresa": empresa,
            "financeiro_preview": financeiro_preview,
        },
    )


@login_required
@admin_required
def procurar_dashboard(request):
    empresa, resposta_erro = _obter_empresa_admin_or_redirect(request)
    if resposta_erro:
        return resposta_erro

    termo = request.GET.get("q", "").strip()
    resultados, totais = obter_resultados_procurar_dashboard(empresa, termo)

    return render(
        request,
        "projetos/procurar_dashboard.html",
        {
            "empresa": empresa,
            "termo": termo,
            "resultados": resultados,
            "totais": totais,
        },
    )


@login_required
@admin_required
def relatorios_exportacao(request):
    empresa, resposta_erro = _obter_empresa_admin_or_redirect(request)
    if resposta_erro:
        return resposta_erro

    return render(
        request,
        "projetos/relatorios_exportacao.html",
        construir_contexto_relatorios_exportacao(
            request=request,
            empresa=empresa,
            listar_projetos_fn=listar_projetos_filtro_exportacao,
            listar_furos_fn=listar_furos_filtro_exportacao,
            construir_cards_fn=construir_cards_datasets,
        ),
    )


@login_required
@admin_required
def relatorios_download(request, dataset, formato):
    empresa, resposta_erro = _obter_empresa_admin_or_redirect(request)
    if resposta_erro:
        return resposta_erro

    filtros = construir_filtros_exportacao(request=request, empresa=empresa)
    dataset_info = obter_dataset_exportacao_service(dataset)
    return construir_resposta_download_dataset(
        dataset=dataset,
        formato=formato,
        dataset_info=dataset_info,
        empresa=empresa,
        filtros=filtros,
        slugify_fn=slugify,
    )


@login_required
@admin_required
def relatorios_download_tudo(request, formato):
    empresa, resposta_erro = _obter_empresa_admin_or_redirect(request)
    if resposta_erro:
        return resposta_erro

    filtros = construir_filtros_exportacao(request=request, empresa=empresa)
    return construir_resposta_download_tudo(
        formato=formato,
        empresa=empresa,
        filtros=filtros,
        slugify_fn=slugify,
    )


@login_required
def sugestoes_plataforma(request):
    if request.method == "POST":
        form = SugestaoPlataformaForm(request.POST)
        resultado = processar_submissao_sugestao(
            form=form,
            user=request.user,
            logger=logger,
        )
        if resultado["estado"] == "ok":
            if resultado["message_level"] == "success":
                messages.success(request, resultado["message_text"])
            else:
                messages.warning(request, resultado["message_text"])
            return redirect("projetos:sugestoes_plataforma")
        messages.error(request, resultado["message_text"])
    else:
        form = SugestaoPlataformaForm()

    return render(
        request,
        "projetos/sugestoes_form.html",
        {
            "form": form,
            "titulo": "Sugestões",
        },
    )
