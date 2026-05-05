import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.text import slugify

from core.permissions import admin_required

from projetos.forms import PreferenciasForm, SugestaoPlataformaForm
from projetos.services.opcoes_exportacao import (
    construir_resposta_download_dataset,
    construir_resposta_download_tudo,
    construir_cards_datasets,
    obter_dataset_exportacao as obter_dataset_exportacao_service,
)
from projetos.services.opcoes import (
    atualizar_financas_projeto,
    atualizar_salario_base_funcao,
    construir_contexto_relatorios_exportacao,
    construir_filtros_exportacao,
    obter_empresa_admin_opcoes,
    processar_fluxo_preferencias_admin_form,
)
from projetos.models import Empregados, SalarioBaseFuncao
from plataforma.services import empresas as empresas_service
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

    if request.method == "POST" and request.POST.get("form_scope") == "empresa_logo":
        acao_logo = (request.POST.get("logo_action") or "upload").strip()
        if acao_logo == "remover":
            resultado_logo = empresas_service.remover_logo_empresa(
                method=request.method,
                empresa=empresa,
            )
        else:
            resultado_logo = empresas_service.atualizar_logo_empresa(
                method=request.method,
                empresa=empresa,
                logo_file=request.FILES.get("logo"),
            )
        if resultado_logo.ok:
            messages.success(request, "Logotipo da empresa atualizado com sucesso.")
        else:
            messages.error(request, resultado_logo.erro or "Não foi possível atualizar o logotipo da empresa.")
        return redirect("projetos:definicoes_admin")

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

    if request.method == "POST" and request.POST.get("form_scope") == "projeto_financas":
        resultado_projeto = atualizar_financas_projeto(
            empresa=empresa,
            projeto_id=request.POST.get("projeto_id"),
            custo_por_metro=request.POST.get("custo_por_metro_cliente_override"),
            outros_gastos=request.POST.get("outros_valores_gastos_associados"),
        )
        if resultado_projeto["ok"]:
            messages.success(request, resultado_projeto["mensagem"])
        else:
            messages.error(request, resultado_projeto["erro"])
        return redirect("projetos:definicoes_financeiras_admin")

    if request.method == "POST" and request.POST.get("form_scope") == "funcao_salario":
        resultado_funcao = atualizar_salario_base_funcao(
            empresa=empresa,
            funcao=request.POST.get("funcao"),
            salario_base=request.POST.get("salario_base"),
        )
        if resultado_funcao["ok"]:
            messages.success(request, resultado_funcao["mensagem"])
        else:
            messages.error(request, resultado_funcao["erro"])
        return redirect("projetos:definicoes_financeiras_admin")

    financeiro_preview = empresa.recalcular_indicadores_financeiros(guardar=False)
    projetos_empresa = list(listar_projetos_filtro_exportacao(empresa))
    total_custo_metro_definido = sum(
        (projeto.custo_por_metro_cliente_override or 0.0) for projeto in projetos_empresa
    )
    total_outros_gastos_definidos = sum(
        (projeto.outros_valores_gastos_associados or 0.0) for projeto in projetos_empresa
    )
    total_geral_definido = total_custo_metro_definido + total_outros_gastos_definidos
    total_metros = float(financeiro_preview.get("total_metros") or 0.0)
    total_despesas = float(financeiro_preview.get("total_despesas") or 0.0)
    total_materiais = float(financeiro_preview.get("valor_total_gasto_materias") or 0.0)
    gasto_furo = float(empresa.valor_total_gasto_furo or 0.0)
    gasto_maquinas = float(empresa.valor_total_gasto_maquinas or 0.0)
    custo_empresa = float(financeiro_preview.get("custo_por_metro_empresa") or 0.0)
    cobrado_cliente = float(financeiro_preview.get("valor_total_cobrado_cliente") or 0.0)
    margem_total = cobrado_cliente - (total_despesas + total_materiais)
    margem_por_metro = (margem_total / total_metros) if total_metros > 0 else 0.0
    salarios_atuais = {
        item["funcao"]: float(item["salario_base"] or 0.0)
        for item in SalarioBaseFuncao.objects.filter(empresa=empresa).values("funcao", "salario_base")
    }
    funcoes_salario = [
        {
            "codigo": codigo,
            "nome": nome,
            "salario_base": salarios_atuais.get(codigo, 0.0),
        }
        for codigo, nome in Empregados.FUNCAO_GERAL_CHOICES
    ]

    return render(
        request,
        "projetos/definicoes_financeiras_admin.html",
        {
            "titulo": "Definições Financeiras da Empresa",
            "empresa": empresa,
            "financeiro_preview": financeiro_preview,
            "projetos_empresa": projetos_empresa,
            "total_custo_metro_definido": round(total_custo_metro_definido, 2),
            "total_outros_gastos_definidos": round(total_outros_gastos_definidos, 2),
            "total_geral_definido": round(total_geral_definido, 2),
            "metricas_financeiras": {
                "custo_empresa": round(custo_empresa, 2),
                "cobrado_cliente": round(cobrado_cliente, 2),
                "gasto_furo": round(gasto_furo, 2),
                "gasto_maquinas": round(gasto_maquinas, 2),
                "gasto_materiais": round(total_materiais, 2),
                "margem_total": round(margem_total, 2),
                "margem_por_metro": round(margem_por_metro, 2),
            },
            "funcoes_salario": funcoes_salario,
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
