from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions import admin_required
from plataforma.models import PerfilPlataforma

from .chat_services import construir_resumo_empresa, gerar_resposta_chat, normalizar_json_chat
from .forms import AnaliseImagemAIForm
from .models import AnaliseImagemAI, ChatMensagemAI, ChatSessaoAI
from .services import executar_analise_imagem


ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


def _obter_empresa_admin_inspecao(request):
    perfil = (
        PerfilPlataforma.objects.filter(
            user=request.user,
            ativo=True,
            tipo_acesso__in=ADMIN_TIPOS_ACESSO_EMPRESA,
        )
        .select_related("empresa")
        .first()
    )
    if not perfil or not perfil.empresa_id:
        messages.error(request, "Não tens permissão para aceder à área de inspeção AI.")
        return None, redirect("projetos:redirect_after_login")
    return perfil.empresa, None


@login_required
@admin_required
def hub(request):
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analises = AnaliseImagemAI.objects.filter(empresa=empresa).select_related("projeto", "furo")
    return render(
        request,
        "inspecao_ai/hub.html",
        {
            "total_analises": analises.count(),
            "total_concluidas": analises.filter(estado="concluida").count(),
            "total_revisao": analises.filter(estado="revisao_manual").count(),
            "analises_recentes": analises[:6],
        },
    )


@login_required
@admin_required
def analise_list(request):
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    estado = (request.GET.get("estado") or "").strip()
    tipo_documento = (request.GET.get("tipo_documento") or "").strip()
    analises = (
        AnaliseImagemAI.objects.filter(empresa=empresa)
        .select_related("projeto", "furo", "criado_por")
        .prefetch_related("deteccoes")
    )
    if estado:
        analises = analises.filter(estado=estado)
    if tipo_documento:
        analises = analises.filter(tipo_documento=tipo_documento)

    return render(
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
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    form = AnaliseImagemAIForm(request.POST or None, request.FILES or None, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        analise = form.save(commit=False)
        analise.empresa = empresa
        analise.criado_por = request.user
        analise.metadados = {
            **(analise.metadados or {}),
            "opcoes_entrada": {
                "auto_corrigir_inclinacao": bool(form.cleaned_data.get("auto_corrigir_inclinacao")),
                "rotacao_manual_graus": float(form.cleaned_data.get("rotacao_manual") or 0),
            },
        }
        analise.save()
        executar_analise_imagem(analise)
        messages.success(
            request,
            "Fotografia enviada com sucesso. A análise visual foi executada e ficou guardada no histórico.",
        )
        return redirect("inspecao_ai:analise_detail", pk=analise.pk)

    return render(
        request,
        "inspecao_ai/analise_form.html",
        {
            "form": form,
            "titulo_pagina": "Nova análise visual AI",
        },
    )


@login_required
@admin_required
def analise_detail(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise = get_object_or_404(
        AnaliseImagemAI.objects.select_related("projeto", "furo", "criado_por").prefetch_related("deteccoes"),
        pk=pk,
        empresa=empresa,
    )
    return render(request, "inspecao_ai/analise_detail.html", {"analise": analise})


@login_required
@admin_required
def analise_reprocessar(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise = get_object_or_404(AnaliseImagemAI, pk=pk, empresa=empresa)
    executar_analise_imagem(analise)
    messages.success(request, "A análise foi reprocessada com o motor visual atual.")
    return redirect("inspecao_ai:analise_detail", pk=analise.pk)


@login_required
@admin_required
def chatbox(request):
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
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
            sessao.ultimo_resumo_contexto = normalizar_json_chat(construir_resumo_empresa(empresa))
            sessao.save(update_fields=["titulo", "ultimo_resumo_contexto", "atualizado_em"])
        return redirect(f"{request.path}?sessao={sessao.pk}")

    resumo = construir_resumo_empresa(empresa)
    return render(
        request,
        "inspecao_ai/chatbox.html",
        {
            "sessao": sessao,
            "sessoes": sessoes,
            "mensagens": sessao.mensagens.all() if sessao else [],
            "resumo_chat": resumo,
        },
    )
