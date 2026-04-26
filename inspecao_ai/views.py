from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
import json

from core.permissions import admin_required
from projetos.models import Furo

from . import domain_logic as dl
from . import workflows as wf
from .chat_services import construir_resumo_empresa
from .forms import AnaliseImagemAIForm
from .models import AnaliseImagemAI
from .selectors.analises import (
    listar_analises_recentes_hub_qs,
    listar_presets_zona_empresa,
    obter_analise_detail_empresa,
    obter_analise_empresa,
    obter_analise_reprocessar_empresa,
)
from .selectors.chat import (
    obter_furo_contexto_chat,
)
from .services.chat import (
    obter_memoria_furo_contexto_sessao,
    obter_sessao_e_lista_chatbox,
    processar_interacao_chat,
)
from .services.biblioteca import construir_contexto_biblioteca
from .services.analises import construir_contexto_analise_detail, construir_contexto_analise_list

def _base_template_inspecao(request):
    return "plataforma/base.html" if request.user.is_superuser else "projetos/base.html"


def _render_inspecao(request, template_name, context):
    context = dict(context or {})
    context.setdefault("base_template", _base_template_inspecao(request))
    return render(request, template_name, context)


@login_required
@admin_required
def hub(request):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analises_qs = listar_analises_recentes_hub_qs(empresa)
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
    documentos_biblioteca = wf.listar_documentos_biblioteca_base_conhecimento()
    contexto_biblioteca = construir_contexto_biblioteca(
        documentos=documentos_biblioteca,
        filtro_leitura=filtro_leitura,
        filtro_extensao=filtro_extensao,
    )

    return _render_inspecao(
        request,
        "inspecao_ai/biblioteca_pdf.html",
        {
            "empresa": empresa,
            "documentos_pdf": contexto_biblioteca["documentos"],
            "biblioteca_path": str((wf.KNOWLEDGE_BASE_ROOT / "pdf").resolve()),
            "extensoes_upload_permitidas": ", ".join(sorted(wf.EXTENSOES_BIBLIOTECA_PERMITIDAS)),
            "filtro_leitura": contexto_biblioteca["filtro_leitura"],
            "filtro_extensao": contexto_biblioteca["filtro_extensao"],
            "filtro_choices": contexto_biblioteca["filtro_choices"],
            "extensao_choices": contexto_biblioteca["extensao_choices"],
            "total_pdfs": contexto_biblioteca["total_pdfs"],
            "total_pdfs_com_txt": contexto_biblioteca["total_pdfs_com_txt"],
            "total_pdfs_sem_txt": contexto_biblioteca["total_pdfs_sem_txt"],
            "total_documentos": contexto_biblioteca["total_documentos"],
            "total_leitura_direta": contexto_biblioteca["total_leitura_direta"],
            "total_txt_auxiliar": contexto_biblioteca["total_txt_auxiliar"],
            "total_nao_preparado": contexto_biblioteca["total_nao_preparado"],
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
    contexto_lista = construir_contexto_analise_list(
        empresa=empresa,
        estado=estado,
        tipo_documento=tipo_documento,
    )

    return _render_inspecao(
        request,
        "inspecao_ai/analise_list.html",
        {
            **contexto_lista,
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
    presets = listar_presets_zona_empresa(empresa)
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

    analise = obter_analise_detail_empresa(pk=pk, empresa=empresa)
    return _render_inspecao(
        request,
        "inspecao_ai/analise_detail.html",
        construir_contexto_analise_detail(analise=analise),
    )


@login_required
@admin_required
def analise_corrigir_campos(request, pk):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise = obter_analise_empresa(pk=pk, empresa=empresa)
    wf.guardar_correcoes_campos(analise, request.POST)
    messages.success(request, "As correções manuais da análise foram guardadas.")
    return redirect("inspecao_ai:analise_detail", pk=analise.pk)


@login_required
@admin_required
def analise_guardar(request, pk):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise = obter_analise_empresa(pk=pk, empresa=empresa)
    wf.guardar_analise_no_historico(analise)
    messages.success(request, "A análise foi guardada no histórico.")
    return redirect("inspecao_ai:analise_detail", pk=analise.pk)


@login_required
@admin_required
def analise_reprocessar(request, pk):
    empresa, resposta_erro = wf.obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise_origem = obter_analise_reprocessar_empresa(pk=pk, empresa=empresa)
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
    sessao, sessoes = obter_sessao_e_lista_chatbox(empresa=empresa, sessao_id=sessao_id)

    if request.method == "POST":
        pergunta = (request.POST.get("pergunta") or "").strip()
        furo_contexto_id = request.POST.get("furo_contexto_id")
        furo_contexto = obter_furo_contexto_chat(empresa=empresa, furo_contexto_id=furo_contexto_id)
        sessao = processar_interacao_chat(
            empresa=empresa,
            utilizador=request.user,
            sessao=sessao,
            pergunta=pergunta,
            furo_contexto=furo_contexto,
        )
        return redirect(f"{request.path}?sessao={sessao.pk}")

    resumo = construir_resumo_empresa(empresa)
    memoria_furo = obter_memoria_furo_contexto_sessao(sessao)
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
