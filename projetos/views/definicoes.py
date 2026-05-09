import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import translation

from core.permissions import user_is_empresa_admin, user_is_geologo
from plataforma.forms import ComplianceScoreConfigForm, GeologiaScoreConfigForm
from plataforma.services import empresas as empresas_service
from projetos.forms import PreferenciasForm
from projetos.services.acesso_contexto import obter_empregado_autenticado_contexto
from projetos.services.definicoes import processar_fluxo_preferencias_utilizador_form
from projetos.selectors.preferencias import (
    garantir_preferencias_empresa,
    obter_ou_criar_preferencias_user,
)

logger = logging.getLogger("core")

# Multiempresa: as preferências devem estar sempre associadas à empresa do utilizador.

def _obter_empregado_autenticado_definicoes(request):
    logger.debug(
        "A resolver empregado autenticado em definicoes.py. user_id=%s, username='%s'",
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
    if ligado_por_fallback and empregado is not None:
        logger.warning(
            "Ligação automática User -> Empregados executada em definicoes.py. user_id=%s, empregado_id=%s, empresa_id=%s, email='%s'",
            request.user.id,
            empregado.id,
            empregado.empresa_id,
            getattr(request.user, "email", ""),
        )
    if resposta_erro:
        logger.warning(
            "Utilizador sem contexto de empregado em definicoes.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro

    return empregado, None


def _aplicar_idioma_preferencias(request, preferencias):
    if preferencias.idioma:
        translation.activate(preferencias.idioma)
        request.session["django_language"] = preferencias.idioma


def _processar_form_definicoes(request, resultado, empregado):
    if not resultado["ok"]:
        logger.warning(
            "Erro ao guardar definições. user_id=%s, empregado_id=%s, erros=%s",
            request.user.id,
            getattr(empregado, "id", None),
            resultado.get("erros_form"),
        )
        messages.error(request, "Erro ao guardar definições.")
        return None

    preferencias = resultado["preferencias"]
    _aplicar_idioma_preferencias(request, preferencias)
    logger.info(
        "Definições atualizadas com sucesso. user_id=%s, empregado_id=%s",
        request.user.id,
        getattr(empregado, "id", None),
    )
    messages.success(request, "Definições guardadas com sucesso.")
    return redirect("projetos:definicoes")

@login_required
def definicoes(request):
    logger.info(
        "Entrada na view definicoes. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_definicoes(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view definicoes. user_id=%s", request.user.id)
        return resposta_erro

    preferencias, _ = obter_ou_criar_preferencias_user(request.user)
    if empregado and empregado.empresa_id:
        preferencias = garantir_preferencias_empresa(preferencias, empregado.empresa)

    geologia_score_form = None
    compliance_score_form = None
    empresa_logo_visivel = bool(empregado and empregado.empresa_id and user_is_empresa_admin(request.user))
    if empregado and empregado.empresa_id and user_is_geologo(request.user):
        geologia_cfg = empresas_service.normalizar_geologia_score_config(
            empregado.empresa.geologia_score_config
        )
        geologia_score_form = GeologiaScoreConfigForm(
            initial={
                "sem_logs": geologia_cfg["pesos"]["sem_logs"],
                "conflito_intervalo": geologia_cfg["pesos"]["conflito_intervalo"],
                "pendente_validacao": geologia_cfg["pesos"]["pendente_validacao"],
                "sem_anexo": geologia_cfg["pesos"]["sem_anexo"],
                "sem_log_24h": geologia_cfg["pesos"]["sem_log_24h"],
                "sem_log_48h": geologia_cfg["pesos"]["sem_log_48h"],
                "janela_atencao_horas": geologia_cfg["janelas_horas"]["atencao"],
                "janela_critico_horas": geologia_cfg["janelas_horas"]["critico"],
            }
        )
    if empregado and empregado.empresa_id and user_is_empresa_admin(request.user):
        compliance_cfg = empresas_service.normalizar_compliance_score_config(
            empregado.empresa.compliance_score_config
        )
        compliance_score_form = ComplianceScoreConfigForm(
            initial={
                "peso_vencidas": compliance_cfg["pesos"]["vencidas"],
                "peso_criticas": compliance_cfg["pesos"]["criticas"],
                "peso_altas": compliance_cfg["pesos"]["altas"],
                "peso_vence_7d": compliance_cfg["pesos"]["vence_7d"],
                "peso_abertas": compliance_cfg["pesos"]["abertas"],
                "threshold_medio": compliance_cfg["thresholds"]["medio"],
                "threshold_alto": compliance_cfg["thresholds"]["alto"],
            }
        )

    if (
        request.method == "POST"
        and request.POST.get("form_scope") == "geologia_score"
        and geologia_score_form is not None
    ):
        geologia_score_form = GeologiaScoreConfigForm(request.POST)
        resultado_geologia = empresas_service.processar_fluxo_geologia_score_config(
            method=request.method,
            empresa=empregado.empresa,
            form=geologia_score_form,
        )
        if resultado_geologia.ok:
            messages.success(request, "Configuração geológica guardada com sucesso.")
            return redirect("projetos:definicoes")
        messages.error(request, "Verifica os valores da configuração geológica e tenta novamente.")

    if (
        request.method == "POST"
        and request.POST.get("form_scope") == "compliance_score"
        and compliance_score_form is not None
    ):
        compliance_score_form = ComplianceScoreConfigForm(request.POST)
        resultado_compliance = empresas_service.processar_fluxo_compliance_score_config(
            method=request.method,
            empresa=empregado.empresa,
            form=compliance_score_form,
        )
        if resultado_compliance.ok:
            messages.success(request, "Configuração de compliance guardada com sucesso.")
            return redirect("projetos:definicoes")
        messages.error(request, "Verifica os valores da configuração de compliance e tenta novamente.")

    if (
        request.method == "POST"
        and request.POST.get("form_scope") == "empresa_logo"
        and empresa_logo_visivel
    ):
        acao_logo = (request.POST.get("logo_action") or "upload").strip()
        if acao_logo == "remover":
            resultado_logo = empresas_service.remover_logo_empresa(
                method=request.method,
                empresa=empregado.empresa,
            )
        else:
            resultado_logo = empresas_service.atualizar_logo_empresa(
                method=request.method,
                empresa=empregado.empresa,
                logo_file=request.FILES.get("logo"),
            )
        if resultado_logo.ok:
            messages.success(request, "Logotipo da empresa atualizado com sucesso.")
            return redirect("projetos:definicoes")
        messages.error(request, resultado_logo.erro or "Não foi possível atualizar o logotipo da empresa.")

    method_preferencias = request.method
    if request.method == "POST" and request.POST.get("form_scope") in {"geologia_score", "empresa_logo", "compliance_score"}:
        method_preferencias = "GET"

    fluxo = processar_fluxo_preferencias_utilizador_form(
        method=method_preferencias,
        post_data=request.POST,
        form_class=PreferenciasForm,
        preferencias=preferencias,
        user=request.user,
        empresa=empregado.empresa if empregado and empregado.empresa_id else None,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta = _processar_form_definicoes(request, resultado, empregado)
        if resposta:
            return resposta

    return render(request, "projetos/definicoes.html", {
        "form": form,
        "geologia_score_form": geologia_score_form,
        "compliance_score_form": compliance_score_form,
        "empresa_logo_visivel": empresa_logo_visivel,
        "empresa_atual": empregado.empresa if empregado else None,
        "titulo": "Definições",
    })
