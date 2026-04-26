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
    TIPOS_REGISTO_CHOICES_EXPORTACAO,
    construir_filtros_exportacao,
    guardar_definicoes_financeiras_admin,
    guardar_preferencias_admin,
    obter_empresa_admin_opcoes,
)
from projetos.services.sugestoes import enviar_sugestao_para_superusers
from projetos.selectors.opcoes import (
    listar_furos_filtro_exportacao,
    listar_projetos_filtro_exportacao,
    obter_resultados_procurar_dashboard,
)
from projetos.selectors.preferencias import (
    garantir_preferencias_empresa,
    obter_ou_criar_preferencias_user,
)
from projetos.models import Despesa

logger = logging.getLogger("core")


@login_required
@admin_required
def definicoes_admin(request):
    empresa, resposta_erro = obter_empresa_admin_opcoes(request=request)
    if resposta_erro:
        return resposta_erro

    preferencias, _ = obter_ou_criar_preferencias_user(request.user)
    preferencias = garantir_preferencias_empresa(preferencias, empresa)

    if request.method == "POST":
        form = PreferenciasForm(request.POST, instance=preferencias, user=request.user, prefix="prefs")
        if form.is_valid():
            preferencias = guardar_preferencias_admin(
                form=form,
                user=request.user,
                empresa=empresa,
            )

            if preferencias.idioma:
                translation.activate(preferencias.idioma)
                request.session["django_language"] = preferencias.idioma

            messages.success(request, "Preferências guardadas com sucesso.")
            return redirect("projetos:definicoes_admin")

        messages.error(request, "Erro ao guardar preferências.")
    else:
        form = PreferenciasForm(instance=preferencias, user=request.user, prefix="prefs")

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
    empresa, resposta_erro = obter_empresa_admin_opcoes(request=request)
    if resposta_erro:
        return resposta_erro

    if request.method == "POST":
        financeiro_form = EmpresaFinanceiraForm(request.POST, instance=empresa, prefix="financeiro")
        if financeiro_form.is_valid():
            empresa = guardar_definicoes_financeiras_admin(
                financeiro_form=financeiro_form,
            )
            messages.success(request, "Definições financeiras guardadas com sucesso.")
            return redirect("projetos:definicoes_financeiras_admin")

        messages.error(request, "Erro ao guardar definições financeiras.")
    else:
        financeiro_form = EmpresaFinanceiraForm(instance=empresa, prefix="financeiro")

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
    empresa, resposta_erro = obter_empresa_admin_opcoes(request=request)
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
    empresa, resposta_erro = obter_empresa_admin_opcoes(request=request)
    if resposta_erro:
        return resposta_erro

    filtros = construir_filtros_exportacao(request=request, empresa=empresa)
    datasets = construir_cards_datasets(empresa, filtros)

    return render(
        request,
        "projetos/relatorios_exportacao.html",
        {
            "empresa": empresa,
            "datasets": datasets,
            "projetos_filtro": listar_projetos_filtro_exportacao(empresa),
            "furos_filtro": listar_furos_filtro_exportacao(empresa=empresa, projeto=filtros.get("projeto")),
            "tipos_registo": [
                *TIPOS_REGISTO_CHOICES_EXPORTACAO,
            ],
            "categorias_despesa": [("", "Todas as categorias"), *Despesa.CATEGORIA_CHOICES],
            "filtros": filtros,
        },
    )


@login_required
@admin_required
def relatorios_download(request, dataset, formato):
    empresa, resposta_erro = obter_empresa_admin_opcoes(request=request)
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
    empresa, resposta_erro = obter_empresa_admin_opcoes(request=request)
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
        form.instance.user = request.user
        if form.is_valid():
            try:
                sugestao = form.save(commit=False)
                try:
                    enviado, email_destino, diagnostico_envio = enviar_sugestao_para_superusers(sugestao=sugestao)
                except Exception:
                    logger.exception(
                        "Falha ao enviar sugestão por email. user_id=%s",
                        request.user.id,
                    )
                    enviado = False
                    email_destino = ""
                    diagnostico_envio = "Falha técnica no envio de email."

                sugestao.enviado_por_email = enviado
                sugestao.email_destino = email_destino
                sugestao.save()

                if diagnostico_envio:
                    logger.warning(
                        "Sugestão sem entrega por email. user_id=%s, destino=%s, diagnostico=%s",
                        request.user.id,
                        email_destino or "-",
                        diagnostico_envio,
                    )

                if enviado:
                    messages.success(
                        request,
                        "Sugestão enviada com sucesso. Obrigado pelo teu contributo.",
                    )
                else:
                    messages.warning(
                        request,
                        f"Sugestão guardada com sucesso. Não foi possível enviar o email neste momento. {diagnostico_envio}",
                    )
                return redirect("projetos:sugestoes_plataforma")
            except Exception:
                logger.exception(
                    "Erro ao processar sugestão na plataforma. user_id=%s",
                    request.user.id,
                )
                messages.error(
                    request,
                    "Ocorreu um erro ao enviar a sugestão. Tenta novamente em instantes.",
                )
        else:
            messages.error(request, "Corrige os campos assinalados para enviar a sugestão.")
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
