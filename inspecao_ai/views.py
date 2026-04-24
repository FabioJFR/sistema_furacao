from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
import json
import re
from pathlib import Path

from core.permissions import admin_required
from plataforma.models import Empresa, PerfilPlataforma
from projetos.models import Furo

from . import domain_logic as dl
from . import workflows as wf
from .chat_services import construir_resumo_empresa, gerar_resposta_chat, normalizar_json_chat
from .forms import AnaliseImagemAIForm
from .models import AnaliseImagemAI, AnaliseZonaPresetAI, ChatMensagemAI, ChatSessaoAI


ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]
KNOWLEDGE_BASE_ROOT = Path(__file__).resolve().parent.parent / "knowledge_base"
EXTENSOES_TEXTO_DIRETO = {
    ".md",
    ".txt",
    ".json",
    ".csv",
    ".log",
    ".ini",
    ".cfg",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".htm",
}
EXTENSOES_BIBLIOTECA_PERMITIDAS = EXTENSOES_TEXTO_DIRETO | {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".odt",
    ".ods",
}


def _base_template_inspecao(request):
    return "plataforma/base.html" if request.user.is_superuser else "projetos/base.html"


def _render_inspecao(request, template_name, context):
    context = dict(context or {})
    context.setdefault("base_template", _base_template_inspecao(request))
    return render(request, template_name, context)


def _normalizar_valor_comparacao_ai(valor):
    return dl.normalizar_valor_comparacao_ai(valor)


def _nome_base_analise_reprocessada(nome):
    return dl.nome_base_analise_reprocessada(nome)


def _parse_zone_payload(raw_value, *, single):
    return dl.parse_zone_payload(raw_value, single=single)


def _construir_resumo_validacao_analise(analise):
    return dl.construir_resumo_validacao_analise(analise)


def _construir_sugestoes_reprocessamento(analise, resumo_validacao):
    return dl.construir_sugestoes_reprocessamento(analise, resumo_validacao)


def _construir_resumo_ai_relatorio(analise):
    return dl.construir_resumo_ai_relatorio(analise)


def _construir_dashboard_aprendizagem_ai(analises):
    return dl.construir_dashboard_aprendizagem_ai(analises)


def _filtrar_analises_visiveis(queryset):
    return dl.filtrar_analises_visiveis(queryset)


def _obter_empresa_admin_inspecao(request):
    return wf.obter_empresa_admin_inspecao(request)


def _listar_documentos_biblioteca_base_conhecimento():
    return wf.listar_documentos_biblioteca_base_conhecimento()


def _normalizar_nome_documento(nome_original):
    return dl.normalizar_nome_documento(nome_original)


def _resolver_path_unico(base_dir, base_nome, extensao):
    return dl.resolver_path_unico(base_dir, base_nome, extensao)


@login_required
@admin_required
def hub(request):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analises_qs = (
        AnaliseImagemAI.objects.filter(empresa=empresa)
        .select_related("projeto", "furo")
        .order_by("-criado_em")
    )
    analises = dl.filtrar_analises_visiveis(list(analises_qs))
    dashboard_aprendizagem = dl.construir_dashboard_aprendizagem_ai(analises)
    return _render_inspecao(
        request,
        "inspecao_ai/hub.html",
        {
            "total_analises": len(analises),
            "total_concluidas": sum(1 for item in analises if item.estado == "concluida"),
            "total_revisao": sum(1 for item in analises if item.estado == "revisao_manual"),
            "analises_recentes": analises[:6],
            "dashboard_aprendizagem": dashboard_aprendizagem,
        },
    )


@login_required
@admin_required
def biblioteca_pdf(request):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    biblioteca_dir = wf.KNOWLEDGE_BASE_ROOT / "pdf"
    biblioteca_dir.mkdir(parents=True, exist_ok=True)

    if request.method == "POST":
        ficheiro = request.FILES.get("documento")
        if not ficheiro:
            messages.error(request, "Seleciona um ficheiro para adicionar à biblioteca.")
            return redirect("inspecao_ai:biblioteca_pdf")

        try:
            destino, txt_criado = wf.guardar_documento_biblioteca(ficheiro)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("inspecao_ai:biblioteca_pdf")

        if destino.name != ficheiro.name:
            messages.success(
                request,
                f"Documento adicionado com sucesso. O nome foi normalizado para {destino.name}."
                + (f" Também foi criado {txt_criado}." if txt_criado else ""),
            )
        else:
            messages.success(
                request,
                "Documento adicionado com sucesso."
                + (f" Também foi criado {txt_criado}." if txt_criado else ""),
            )

        return redirect("inspecao_ai:biblioteca_pdf")

    filtro_leitura = (request.GET.get("leitura") or "todas").strip()
    filtro_extensao = (request.GET.get("extensao") or "todas").strip()
    documentos_pdf = wf.listar_documentos_biblioteca_base_conhecimento()
    if filtro_leitura == "direta":
        documentos_pdf = [item for item in documentos_pdf if item["leitura"] == "direta"]
    elif filtro_leitura == "txt_auxiliar":
        documentos_pdf = [item for item in documentos_pdf if item["leitura"] == "txt_auxiliar"]
    elif filtro_leitura == "nao_preparado":
        documentos_pdf = [item for item in documentos_pdf if item["leitura"] == "nao_preparado"]
    if filtro_extensao != "todas":
        documentos_pdf = [item for item in documentos_pdf if item["extensao"] == filtro_extensao]

    extensoes_disponiveis = sorted(
        {
            item["extensao"]
            for item in wf.listar_documentos_biblioteca_base_conhecimento()
            if item["extensao"] and item["extensao"] != "(sem extensão)"
        }
    )

    return _render_inspecao(
        request,
        "inspecao_ai/biblioteca_pdf.html",
        {
            "empresa": empresa,
            "documentos_pdf": documentos_pdf,
            "biblioteca_path": str((wf.KNOWLEDGE_BASE_ROOT / "pdf").resolve()),
            "extensoes_upload_permitidas": ", ".join(sorted(wf.EXTENSOES_BIBLIOTECA_PERMITIDAS)),
            "filtro_leitura": filtro_leitura,
            "filtro_extensao": filtro_extensao,
            "filtro_choices": [
                ("todas", "Todos"),
                ("direta", "Leitura direta"),
                ("txt_auxiliar", "TXT auxiliar"),
                ("nao_preparado", "Não preparado"),
            ],
            "extensao_choices": [("todas", "Todas")] + [(item, item) for item in extensoes_disponiveis],
            "total_pdfs": sum(1 for item in documentos_pdf if item["extensao"] == ".pdf"),
            "total_pdfs_com_txt": sum(1 for item in documentos_pdf if item["extensao"] == ".pdf" and item["tem_txt"]),
            "total_pdfs_sem_txt": sum(1 for item in documentos_pdf if item["extensao"] == ".pdf" and not item["tem_txt"]),
            "total_documentos": len(documentos_pdf),
            "total_leitura_direta": sum(1 for item in documentos_pdf if item["leitura"] == "direta"),
            "total_txt_auxiliar": sum(1 for item in documentos_pdf if item["leitura"] == "txt_auxiliar"),
            "total_nao_preparado": sum(1 for item in documentos_pdf if item["leitura"] == "nao_preparado"),
        },
    )



def construir_memoria_operacional_furo(furo):
    return dl.construir_memoria_operacional_furo(furo)


@login_required
@admin_required
def memoria_operacional(request):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    termo = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    com_coordenadas = (request.GET.get("com_coordenadas") or "").strip() == "1"
    despesas_altas = (request.GET.get("despesas_altas") or "").strip() == "1"
    ordenar = (request.GET.get("ordenar") or "recentes").strip()

    furos, memoria_cards = wf.aplicar_filtros_memoria_operacional(
        empresa=empresa,
        termo=termo,
        estado=estado,
        com_coordenadas=com_coordenadas,
        despesas_altas=despesas_altas,
        ordenar=ordenar,
    )

    return _render_inspecao(
        request,
        "inspecao_ai/memoria_operacional.html",
        {
            "termo": termo,
            "estado": estado,
            "com_coordenadas": com_coordenadas,
            "despesas_altas": despesas_altas,
            "ordenar": ordenar,
            "furos": furos,
            "memoria_cards": memoria_cards,
            "estado_choices": Furo.ESTADO_CHOICES,
            "ordenacao_choices": [
                ("recentes", "Mais recentes"),
                ("profundos", "Mais profundos"),
                ("caros", "Mais caros"),
                ("medicoes", "Com mais medições"),
            ],
        },
    )


@login_required
@admin_required
def analise_list(request):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    estado = (request.GET.get("estado") or "").strip()
    tipo_documento = (request.GET.get("tipo_documento") or "").strip()
    analises_qs = (
        AnaliseImagemAI.objects.filter(empresa=empresa)
        .select_related("projeto", "furo", "criado_por")
        .prefetch_related("deteccoes")
    )
    if estado:
        analises_qs = analises_qs.filter(estado=estado)
    if tipo_documento:
        analises_qs = analises_qs.filter(tipo_documento=tipo_documento)
    analises = dl.filtrar_analises_visiveis(list(analises_qs))

    return _render_inspecao(
        request,
        "inspecao_ai/analise_list.html",
        {
            "analises": analises,
            "estado_atual": estado,
            "tipo_documento_atual": tipo_documento,
            "estado_choices": AnaliseImagemAI.ESTADO_CHOICES,
            "tipo_documento_choices": AnaliseImagemAI.TIPO_DOCUMENTO_CHOICES,
        },
    )


@login_required
@admin_required
def analise_create(request):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    form = AnaliseImagemAIForm(request.POST or None, request.FILES or None, empresa=empresa)
    presets = list(
        AnaliseZonaPresetAI.objects.filter(empresa=empresa)
        .order_by("tipo_documento", "nome")
        .values("id", "nome", "tipo_documento", "zona_relatorio", "zonas_texto")
    )
    if request.method == "POST" and form.is_valid():
        analise = wf.criar_analise_preview(form=form, empresa=empresa, user=request.user)
        messages.success(
            request,
            "A análise visual foi executada. Revê o resultado e carrega em guardar se quiseres colocá-la no histórico.",
        )
        return redirect("inspecao_ai:analise_detail", pk=analise.pk)

    return _render_inspecao(
        request,
        "inspecao_ai/analise_form.html",
        {
            "form": form,
            "titulo_pagina": "Nova análise visual AI",
            "zona_presets": presets,
        },
    )


@login_required
@admin_required
def zona_preset_guardar(request):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return JsonResponse({"ok": False, "error": "Sem acesso à empresa atual."}, status=403)

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método inválido."}, status=405)

    nome = (request.POST.get("nome") or "").strip()
    tipo_documento = (request.POST.get("tipo_documento") or "").strip() or "relatorio_trabalhador"
    report_zone = (request.POST.get("report_zone_json") or "").strip()
    custom_zones = (request.POST.get("custom_text_zones_json") or "").strip()

    if not nome:
        return JsonResponse({"ok": False, "error": "Indica um nome para o preset."}, status=400)

    try:
        preset = wf.guardar_preset_zonas(
            empresa=empresa,
            user=request.user,
            nome=nome,
            tipo_documento=tipo_documento,
            report_zone_raw=report_zone,
            custom_zones_raw=custom_zones,
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "As zonas definidas são inválidas."}, status=400)
    return JsonResponse(
        {
            "ok": True,
            "preset": {
                "id": str(preset.pk),
                "nome": preset.nome,
                "tipo_documento": preset.tipo_documento,
                "zona_relatorio": preset.zona_relatorio or {},
                "zonas_texto": preset.zonas_texto or [],
            },
        }
    )


@login_required
@admin_required
def analise_detail(request, pk):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise = get_object_or_404(
        AnaliseImagemAI.objects.select_related("projeto", "furo", "criado_por").prefetch_related("deteccoes"),
        pk=pk,
        empresa=empresa,
    )
    resumo_validacao = dl.construir_resumo_validacao_analise(analise)
    sugestoes_reprocessamento = dl.construir_sugestoes_reprocessamento(analise, resumo_validacao)
    resumo_ai_relatorio = dl.construir_resumo_ai_relatorio(analise)
    return _render_inspecao(
        request,
        "inspecao_ai/analise_detail.html",
        {
            "analise": analise,
            "resumo_validacao": resumo_validacao,
            "sugestoes_reprocessamento": sugestoes_reprocessamento,
            "resumo_ai_relatorio": resumo_ai_relatorio,
        },
    )


@login_required
@admin_required
def analise_corrigir_campos(request, pk):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise = get_object_or_404(AnaliseImagemAI, pk=pk, empresa=empresa)
    wf.guardar_correcoes_campos(analise, request.POST)
    messages.success(request, "As correções manuais da análise foram guardadas.")
    return redirect("inspecao_ai:analise_detail", pk=analise.pk)


@login_required
@admin_required
def analise_guardar(request, pk):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise = get_object_or_404(AnaliseImagemAI, pk=pk, empresa=empresa)
    wf.guardar_analise_no_historico(analise)
    messages.success(request, "A análise foi guardada no histórico.")
    return redirect("inspecao_ai:analise_detail", pk=analise.pk)


@login_required
@admin_required
def analise_reprocessar(request, pk):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise_origem = get_object_or_404(
        AnaliseImagemAI.objects.select_related("projeto", "furo", "criado_por"),
        pk=pk,
        empresa=empresa,
    )
    relatorio_focus = (request.POST.get("relatorio_focus") or "").strip()
    nova_analise, foco_labels = wf.reprocessar_analise(
        analise_origem=analise_origem,
        user=request.user,
        relatorio_focus=relatorio_focus,
    )
    if relatorio_focus:
        messages.success(
            request,
            f"Foi criada uma nova análise focada em {foco_labels.get(relatorio_focus, relatorio_focus)} com a foto original e o motor atual.",
        )
    else:
        messages.success(
            request,
            "Foi criada uma nova análise com a foto original e processada com as atualizações mais recentes do motor.",
        )
    return redirect("inspecao_ai:analise_detail", pk=nova_analise.pk)


@login_required
@admin_required
def chatbox(request):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    sessao_id = request.GET.get("sessao") or request.POST.get("sessao_id")
    sessoes = ChatSessaoAI.objects.filter(empresa=empresa, ativa=True).prefetch_related("mensagens")[:12]
    sessao = None
    if sessao_id:
        sessao = get_object_or_404(ChatSessaoAI, pk=sessao_id, empresa=empresa)
    else:
        sessao = sessoes[0] if sessoes else None

    if request.method == "POST":
        pergunta = (request.POST.get("pergunta") or "").strip()
        furo_contexto_id = request.POST.get("furo_contexto_id")
        furo_contexto = None
        if furo_contexto_id:
            furo_contexto = Furo.objects.filter(empresa=empresa, pk=furo_contexto_id).select_related("projeto").first()
        if not sessao:
            sessao = ChatSessaoAI.objects.create(
                empresa=empresa,
                utilizador=request.user,
                titulo=(pergunta[:80] or "Nova conversa AI"),
            )
        if pergunta:
            ChatMensagemAI.objects.create(sessao=sessao, papel="user", conteudo=pergunta)
            resposta, metadados = gerar_resposta_chat(empresa=empresa, pergunta=pergunta)
            ChatMensagemAI.objects.create(
                sessao=sessao,
                papel="assistant",
                conteudo=resposta,
                metadados=normalizar_json_chat(metadados),
            )
            if sessao.titulo == "Nova conversa AI":
                sessao.titulo = pergunta[:80]
            resumo_contexto = construir_resumo_empresa(empresa)
            if furo_contexto:
                resumo_contexto["memoria_furo_contexto"] = dl.construir_memoria_operacional_furo(furo_contexto)
            sessao.ultimo_resumo_contexto = normalizar_json_chat(resumo_contexto)
            sessao.save(update_fields=["titulo", "ultimo_resumo_contexto", "atualizado_em"])
        return redirect(f"{request.path}?sessao={sessao.pk}")

    resumo = construir_resumo_empresa(empresa)
    memoria_furo = None
    if sessao and sessao.ultimo_resumo_contexto:
        memoria_furo = sessao.ultimo_resumo_contexto.get("memoria_furo_contexto")
    return _render_inspecao(
        request,
        "inspecao_ai/chatbox.html",
        {
            "sessao": sessao,
            "sessoes": sessoes,
            "mensagens": sessao.mensagens.all() if sessao else [],
            "resumo_chat": resumo,
            "memoria_furo_contexto": memoria_furo,
        },
    )
