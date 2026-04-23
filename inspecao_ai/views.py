from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
import json
import re
from pathlib import Path

from core.permissions import admin_required
from plataforma.models import Empresa, PerfilPlataforma
from projetos.models import Furo

from .chat_services import construir_resumo_empresa, gerar_resposta_chat, normalizar_json_chat
from .forms import AnaliseImagemAIForm
from .models import AnaliseImagemAI, AnaliseZonaPresetAI, ChatMensagemAI, ChatSessaoAI
from .services import executar_analise_imagem


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
    texto = (valor or "").strip().lower()
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.replace("ã", "a").replace("á", "a").replace("à", "a").replace("â", "a")
    texto = texto.replace("é", "e").replace("ê", "e")
    texto = texto.replace("í", "i")
    texto = texto.replace("ó", "o").replace("ô", "o").replace("õ", "o")
    texto = texto.replace("ú", "u")
    texto = re.sub(r"[^a-z0-9./:,\- ]", "", texto)
    return texto.strip()


def _nome_base_analise_reprocessada(nome):
    base = (nome or "").strip()
    if not base:
        return "Análise"
    suffixes = {
        "Data",
        "Turno",
        "Equipa",
        "Observações",
        "Área central do relatório",
        "Faixa superior impressa",
        "Rodapé impresso",
        "reprocessada",
    }
    parts = [part.strip() for part in base.split("·")]
    while len(parts) > 1 and parts[-1] in suffixes:
        parts.pop()
    cleaned = " · ".join(part for part in parts if part)
    return cleaned or base


def _parse_zone_payload(raw_value, *, single):
    if not raw_value:
        return None if single else []
    parsed = json.loads(raw_value)
    zones = [parsed] if single and isinstance(parsed, dict) else parsed
    if not isinstance(zones, list):
        raise ValueError("Formato inválido.")
    cleaned = []
    for zone in zones:
        if not isinstance(zone, dict):
            raise ValueError("Zona inválida.")
        item = {
            "x_percent": round(float(zone.get("x_percent") or 0), 2),
            "y_percent": round(float(zone.get("y_percent") or 0), 2),
            "w_percent": round(float(zone.get("w_percent") or 0), 2),
            "h_percent": round(float(zone.get("h_percent") or 0), 2),
        }
        if min(item["x_percent"], item["y_percent"]) < 0 or min(item["w_percent"], item["h_percent"]) <= 0:
            raise ValueError("Zona fora dos limites.")
        if item["x_percent"] + item["w_percent"] > 100.0 + 1e-6 or item["y_percent"] + item["h_percent"] > 100.0 + 1e-6:
            raise ValueError("Zona fora dos limites.")
        nome = (zone.get("name") or "").strip()
        if nome:
            item["name"] = nome[:80]
        cleaned.append(item)
    return cleaned[0] if single else cleaned


def _construir_resumo_validacao_analise(analise):
    campos = list(((analise.campos_extraidos or {}).get("campos") or []))
    total_validados = 0
    total_acertos = 0
    total_falhas = 0

    for campo in campos:
        valor_lido = campo.get("valor_validado") if campo.get("validado_utilizador") and campo.get("valor_validado") else campo.get("valor_lido")
        campo["valor_validado"] = campo.get("valor_validado") or ""
        campo["comparacao_estado"] = "sem_validacao"
        campo["comparacao_label"] = "Sem validação"

        if not campo.get("validado_utilizador") or not campo.get("valor_validado"):
            continue

        total_validados += 1
        valor_ai = _normalizar_valor_comparacao_ai(campo.get("valor_lido"))
        valor_validado = _normalizar_valor_comparacao_ai(campo.get("valor_validado"))

        if valor_ai and valor_ai == valor_validado:
            campo["comparacao_estado"] = "acertou"
            campo["comparacao_label"] = "AI acertou"
            total_acertos += 1
        else:
            campo["comparacao_estado"] = "falhou"
            campo["comparacao_label"] = "AI falhou"
            total_falhas += 1

    taxa_acerto = round((total_acertos / total_validados) * 100, 1) if total_validados else None
    return {
        "campos": campos,
        "total_validados": total_validados,
        "total_acertos": total_acertos,
        "total_falhas": total_falhas,
        "taxa_acerto": taxa_acerto,
    }


def _construir_sugestoes_reprocessamento(analise, resumo_validacao):
    if analise.tipo_documento != "relatorio_trabalhador":
        return []

    sugestoes = []
    vistos = set()
    mapping = {
        "data": ("data", "Reanalisar Data", "A validação indica que o campo de data ainda precisa de foco dedicado."),
        "turno": ("turno", "Reanalisar Turno", "O turno validado não bateu certo com a leitura atual da AI."),
        "equipa": ("equipa", "Reanalisar Equipa", "A identificação da equipa continua fraca e merece nova tentativa focada."),
        "observacoes": ("observacoes", "Reanalisar área central do relatório", "A escrita manual da área central do relatório continua a falhar na leitura estimada."),
    }

    for campo in resumo_validacao["campos"]:
        if campo.get("comparacao_estado") != "falhou":
            continue
        semantic = (campo.get("campo_semantico") or "").strip()
        if semantic not in mapping or semantic in vistos:
            continue
        vistos.add(semantic)
        focus, label, reason = mapping[semantic]
        sugestoes.append(
            {
                "focus": focus,
                "label": label,
                "reason": reason,
            }
        )

    if not sugestoes and resumo_validacao["total_falhas"] > 0:
        sugestoes.append(
            {
                "focus": "",
                "label": "Reanalisar relatório completo",
                "reason": "Existem falhas validadas, mas sem um campo semântico claro para isolar a próxima tentativa.",
            }
        )

    return sugestoes


def _construir_resumo_ai_relatorio(analise):
    if analise.tipo_documento != "relatorio_trabalhador":
        return []

    campos = list(((analise.campos_extraidos or {}).get("campos") or []))
    secoes = {
        "Topo esquerdo": [],
        "Topo direito": [],
        "Área central": [],
        "Zona inferior": [],
    }
    semantic_to_section = {
        "cliente": "Topo esquerdo",
        "estaleiro": "Topo esquerdo",
        "sondagem_numero": "Topo esquerdo",
        "inclinacao": "Topo esquerdo",
        "perfil_furacao": "Topo esquerdo",
        "data": "Topo direito",
        "turno": "Topo direito",
        "profundidade_inicio": "Topo direito",
        "profundidade_final": "Topo direito",
        "avanco_turno": "Topo direito",
        "testemunho_recuperado": "Topo direito",
        "recuperacao_percentual": "Topo direito",
        "tempos": "Área central",
        "parametros": "Área central",
        "furacao_registo": "Área central",
        "observacoes": "Área central",
        "assinatura_equipa": "Zona inferior",
        "rodape_validacao": "Zona inferior",
        "identificacao_relatorio": "Topo esquerdo",
    }

    for campo in campos:
        titulo = campo.get("campo_impresso") or campo.get("campo") or "Campo do relatório"
        valor = campo.get("valor_preenchido_trabalhador") or campo.get("valor_lido") or "-"
        section = semantic_to_section.get(campo.get("campo_semantico"), "Área central")
        secoes.setdefault(section, []).append(f"{titulo}: {valor}")

    resumo = []
    for section, linhas in secoes.items():
        if not linhas:
            continue
        resumo.append(section)
        resumo.extend(linhas)
    return resumo


def _construir_dashboard_aprendizagem_ai(analises):
    total_validados = 0
    total_acertos = 0
    total_falhas = 0
    por_tipo = {}
    por_campo = {}
    ultimas_validacoes = []

    for analise in analises:
        tipo = analise.tipo_documento
        tipo_item = por_tipo.setdefault(
            tipo,
            {
                "label": analise.get_tipo_documento_display(),
                "total_validados": 0,
                "total_acertos": 0,
                "total_falhas": 0,
                "taxa_acerto": None,
            },
        )

        for campo in ((analise.campos_extraidos or {}).get("campos") or []):
            if not campo.get("validado_utilizador") or not campo.get("valor_validado"):
                continue

            total_validados += 1
            tipo_item["total_validados"] += 1

            valor_ai = _normalizar_valor_comparacao_ai(campo.get("valor_lido"))
            valor_validado = _normalizar_valor_comparacao_ai(campo.get("valor_validado"))
            acertou = bool(valor_ai and valor_ai == valor_validado)

            campo_chave = campo.get("campo_semantico") or campo.get("campo") or "campo_livre"
            campo_item = por_campo.setdefault(
                campo_chave,
                {
                    "label": campo_chave.replace("_", " "),
                    "total_validados": 0,
                    "total_acertos": 0,
                    "total_falhas": 0,
                    "taxa_acerto": None,
                },
            )
            campo_item["total_validados"] += 1

            if acertou:
                total_acertos += 1
                tipo_item["total_acertos"] += 1
                campo_item["total_acertos"] += 1
            else:
                total_falhas += 1
                tipo_item["total_falhas"] += 1
                campo_item["total_falhas"] += 1

            ultimas_validacoes.append(
                {
                    "analise_id": analise.pk,
                    "analise_nome": analise.nome,
                    "criado_em": analise.criado_em,
                    "tipo_documento": analise.get_tipo_documento_display(),
                    "campo_label": campo_item["label"],
                    "valor_ai": campo.get("valor_lido") or "-",
                    "valor_validado": campo.get("valor_validado") or "-",
                    "estado": "acertou" if acertou else "falhou",
                }
            )

    for item in por_tipo.values():
        if item["total_validados"]:
            item["taxa_acerto"] = round((item["total_acertos"] / item["total_validados"]) * 100, 1)

    for item in por_campo.values():
        if item["total_validados"]:
            item["taxa_acerto"] = round((item["total_acertos"] / item["total_validados"]) * 100, 1)

    ranking_problematicos = [
        item
        for item in sorted(
            por_campo.values(),
            key=lambda item: (-item["total_falhas"], item["taxa_acerto"] if item["taxa_acerto"] is not None else 999, item["label"]),
        )
        if item["total_falhas"] > 0
    ][:6]

    ultimas_validacoes = sorted(ultimas_validacoes, key=lambda item: item["criado_em"], reverse=True)[:10]

    return {
        "total_validados": total_validados,
        "total_acertos": total_acertos,
        "total_falhas": total_falhas,
        "taxa_acerto_global": round((total_acertos / total_validados) * 100, 1) if total_validados else None,
        "por_tipo": sorted(por_tipo.values(), key=lambda item: (-item["total_validados"], item["label"])),
        "por_campo": sorted(por_campo.values(), key=lambda item: (-item["total_validados"], item["label"])),
        "ranking_problematicos": ranking_problematicos,
        "ultimas_validacoes": ultimas_validacoes,
    }


def _filtrar_analises_visiveis(queryset):
    resultado = []
    for analise in queryset:
        opcoes = ((analise.metadados or {}).get("opcoes_entrada") or {})
        preview_mode = bool(opcoes.get("preview_mode"))
        if preview_mode and not analise.guardada:
            continue
        resultado.append(analise)
    return resultado


def _obter_empresa_admin_inspecao(request):
    if request.user.is_superuser:
        empresa_id = (request.GET.get("empresa") or request.POST.get("empresa") or "").strip()
        empresa_qs = Empresa.objects.all().order_by("nome")
        if empresa_id:
            empresa = empresa_qs.filter(pk=empresa_id).first()
            if empresa:
                return empresa, None
        empresa = empresa_qs.first()
        if empresa:
            return empresa, None
        messages.error(request, "Ainda não existe nenhuma empresa disponível para abrir a área de inspeção AI.")
        return None, redirect("plataforma:dashboard")

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


def _listar_documentos_biblioteca_base_conhecimento():
    pdf_root = KNOWLEDGE_BASE_ROOT / "pdf"
    if not pdf_root.exists():
        return []

    documentos = []
    for path in sorted(pdf_root.rglob("*")):
        if not path.is_file() or path.name.startswith(".") or path.name.lower() == "readme.md":
            continue
        sidecar_txt = path.with_suffix(".txt")
        extensao = path.suffix.lower()
        leitura = "direta" if extensao in EXTENSOES_TEXTO_DIRETO else ("txt_auxiliar" if sidecar_txt.exists() else "nao_preparado")
        documentos.append(
            {
                "nome": path.name,
                "relativo": str(path.relative_to(KNOWLEDGE_BASE_ROOT)),
                "txt_relativo": str(sidecar_txt.relative_to(KNOWLEDGE_BASE_ROOT)) if sidecar_txt.exists() else "",
                "tem_txt": sidecar_txt.exists(),
                "extensao": extensao or "(sem extensão)",
                "tamanho_kb": round(path.stat().st_size / 1024, 1) if path.exists() else 0,
                "leitura": leitura,
            }
        )
    return documentos


def _normalizar_nome_documento(nome_original):
    path = Path(nome_original or "")
    extensao = path.suffix.lower().strip()
    base = slugify(path.stem or "")
    if not base:
        base = "documento"
    return base, extensao


def _resolver_path_unico(base_dir, base_nome, extensao):
    candidato = base_dir / f"{base_nome}{extensao}"
    indice = 2
    while candidato.exists():
        candidato = base_dir / f"{base_nome}-{indice}{extensao}"
        indice += 1
    return candidato


@login_required
@admin_required
def hub(request):
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analises_qs = (
        AnaliseImagemAI.objects.filter(empresa=empresa)
        .select_related("projeto", "furo")
        .order_by("-criado_em")
    )
    analises = _filtrar_analises_visiveis(list(analises_qs))
    dashboard_aprendizagem = _construir_dashboard_aprendizagem_ai(analises)
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
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    biblioteca_dir = KNOWLEDGE_BASE_ROOT / "pdf"
    biblioteca_dir.mkdir(parents=True, exist_ok=True)

    if request.method == "POST":
        ficheiro = request.FILES.get("documento")
        if not ficheiro:
            messages.error(request, "Seleciona um ficheiro para adicionar à biblioteca.")
            return redirect("inspecao_ai:biblioteca_pdf")

        base_nome, extensao = _normalizar_nome_documento(ficheiro.name)
        if not extensao:
            messages.error(request, "O ficheiro precisa de ter uma extensão reconhecível.")
            return redirect("inspecao_ai:biblioteca_pdf")

        if extensao not in EXTENSOES_BIBLIOTECA_PERMITIDAS:
            messages.error(
                request,
                f"A extensão {extensao} não está permitida nesta biblioteca.",
            )
            return redirect("inspecao_ai:biblioteca_pdf")

        destino = _resolver_path_unico(biblioteca_dir, base_nome, extensao)
        with destino.open("wb") as output_file:
            for chunk in ficheiro.chunks():
                output_file.write(chunk)

        txt_criado = ""
        if extensao == ".pdf":
            txt_path = destino.with_suffix(".txt")
            if not txt_path.exists():
                txt_path.write_text(
                    (
                        f"Ficheiro auxiliar criado automaticamente para {destino.name}.\n\n"
                        "Coloca aqui o texto extraído, resumo fiel ou notas principais do PDF para a AI consultar.\n"
                    ),
                    encoding="utf-8",
                )
            txt_criado = txt_path.name

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
    documentos_pdf = _listar_documentos_biblioteca_base_conhecimento()
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
            for item in _listar_documentos_biblioteca_base_conhecimento()
            if item["extensao"] and item["extensao"] != "(sem extensão)"
        }
    )

    return _render_inspecao(
        request,
        "inspecao_ai/biblioteca_pdf.html",
        {
            "empresa": empresa,
            "documentos_pdf": documentos_pdf,
            "biblioteca_path": str((KNOWLEDGE_BASE_ROOT / "pdf").resolve()),
            "extensoes_upload_permitidas": ", ".join(sorted(EXTENSOES_BIBLIOTECA_PERMITIDAS)),
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
    projeto = getattr(furo, "projeto", None)

    profundidade_planeada = getattr(furo, "profundidade", None)
    profundidade_atingida = getattr(furo, "profundidade_maxima_atingida", None)

    if profundidade_atingida in [None, ""] and profundidade_planeada not in [None, ""]:
        profundidade_atingida = profundidade_planeada

    total_despesas = getattr(furo, "total_despesas_diretas", None)
    total_medicoes = getattr(furo, "total_medicoes_registadas", None)

    tem_coordenadas = bool(
        getattr(furo, "latitude", None) not in [None, ""]
        and getattr(furo, "longitude", None) not in [None, ""]
    )

    resumo = {
        "id": str(furo.pk),
        "nome": getattr(furo, "nome", "") or f"Furo {furo.pk}",
        "projeto_id": str(projeto.pk) if projeto else None,
        "projeto_nome": getattr(projeto, "nome", "") if projeto else "",
        "estado": getattr(furo, "estado", "") or "",
        "estado_label": getattr(furo, "get_estado_display", lambda: getattr(furo, "estado", ""))(),
        "data": getattr(furo, "data", None),
        "localizacao": getattr(furo, "localizacao", "") or "",
        "local_sondagem": getattr(furo, "local_sondagem", "") or "",
        "latitude": getattr(furo, "latitude", None),
        "longitude": getattr(furo, "longitude", None),
        "tem_coordenadas": tem_coordenadas,
        "profundidade_planeada": profundidade_planeada,
        "profundidade_atingida": profundidade_atingida,
        "total_despesas_diretas": float(total_despesas or 0),
        "total_medicoes_registadas": int(total_medicoes or 0),
        "observacoes": getattr(furo, "observacoes", "") or "",
    }

    destaques = []

    if resumo["projeto_nome"]:
        destaques.append(f"Projeto: {resumo['projeto_nome']}")

    if resumo["estado_label"]:
        destaques.append(f"Estado: {resumo['estado_label']}")

    if resumo["profundidade_atingida"] not in [None, ""]:
        destaques.append(f"Profundidade: {resumo['profundidade_atingida']} m")

    if resumo["total_medicoes_registadas"]:
        destaques.append(f"Medições: {resumo['total_medicoes_registadas']}")

    if resumo["total_despesas_diretas"]:
        destaques.append(f"Despesas diretas: {resumo['total_despesas_diretas']:.2f}")

    if resumo["tem_coordenadas"]:
        destaques.append("Com coordenadas")

    resumo["destaques"] = destaques

    texto_memoria = []
    texto_memoria.append(f"Furo: {resumo['nome']}")

    if resumo["projeto_nome"]:
        texto_memoria.append(f"Projeto: {resumo['projeto_nome']}")

    if resumo["estado_label"]:
        texto_memoria.append(f"Estado: {resumo['estado_label']}")

    if resumo["localizacao"]:
        texto_memoria.append(f"Localização: {resumo['localizacao']}")

    if resumo["local_sondagem"]:
        texto_memoria.append(f"Local de sondagem: {resumo['local_sondagem']}")

    if resumo["profundidade_planeada"] not in [None, ""]:
        texto_memoria.append(f"Profundidade planeada: {resumo['profundidade_planeada']} m")

    if resumo["profundidade_atingida"] not in [None, ""]:
        texto_memoria.append(f"Profundidade atingida: {resumo['profundidade_atingida']} m")

    if resumo["total_medicoes_registadas"]:
        texto_memoria.append(f"Total de medições: {resumo['total_medicoes_registadas']}")

    if resumo["total_despesas_diretas"]:
        texto_memoria.append(f"Despesas diretas acumuladas: {resumo['total_despesas_diretas']:.2f}")

    if resumo["tem_coordenadas"]:
        texto_memoria.append(
            f"Coordenadas: {resumo['latitude']}, {resumo['longitude']}"
        )

    if resumo["observacoes"]:
        texto_memoria.append(f"Observações: {resumo['observacoes']}")

    resumo["texto_memoria"] = " | ".join(texto_memoria)

    return resumo


@login_required
@admin_required
def memoria_operacional(request):
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    termo = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    com_coordenadas = (request.GET.get("com_coordenadas") or "").strip() == "1"
    despesas_altas = (request.GET.get("despesas_altas") or "").strip() == "1"
    ordenar = (request.GET.get("ordenar") or "recentes").strip()

    furos_qs = (
        Furo.objects.filter(empresa=empresa)
        .select_related("projeto")
        .annotate(
            total_despesas_diretas=Sum("despesas__valor"),
            total_medicoes_registadas=Count("medicoes", distinct=True),
        )
    )
    if termo:
        furos_qs = furos_qs.filter(
            Q(nome__icontains=termo)
            | Q(localizacao__icontains=termo)
            | Q(local_sondagem__icontains=termo)
            | Q(projeto__nome__icontains=termo)
        )
    if estado:
        furos_qs = furos_qs.filter(estado=estado)
    if com_coordenadas:
        furos_qs = furos_qs.filter(latitude__isnull=False, longitude__isnull=False)
    if despesas_altas:
        furos_qs = furos_qs.filter(total_despesas_diretas__gte=1000)

    ordenacao_map = {
        "recentes": ("-data",),
        "profundos": ("-profundidade_maxima_atingida", "-data"),
        "caros": ("-total_despesas_diretas", "-data"),
        "medicoes": ("-total_medicoes_registadas", "-data"),
    }
    furos_qs = furos_qs.order_by(*ordenacao_map.get(ordenar, ("-data",)))

    furos = list(furos_qs[:24])
    memoria_cards = []
    for furo in furos:
        memoria_cards.append(construir_memoria_operacional_furo(furo))

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
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
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
    analises = _filtrar_analises_visiveis(list(analises_qs))

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
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    form = AnaliseImagemAIForm(request.POST or None, request.FILES or None, empresa=empresa)
    presets = list(
        AnaliseZonaPresetAI.objects.filter(empresa=empresa)
        .order_by("tipo_documento", "nome")
        .values("id", "nome", "tipo_documento", "zona_relatorio", "zonas_texto")
    )
    if request.method == "POST" and form.is_valid():
        analise = form.save(commit=False)
        analise.empresa = empresa
        analise.criado_por = request.user
        analise.guardada = False
        analise.metadados = {
            **(analise.metadados or {}),
            "opcoes_entrada": {
                "auto_corrigir_inclinacao": bool(form.cleaned_data.get("auto_corrigir_inclinacao")),
                "rotacao_manual_graus": float(form.cleaned_data.get("rotacao_manual") or 0),
                "relatorio_focus": (form.cleaned_data.get("relatorio_focus") or "").strip(),
                "zona_relatorio": form.cleaned_data.get("report_zone") or None,
                "area_prioritaria": {
                    "x_percent": float(form.cleaned_data.get("area_x_percent") or 0),
                    "y_percent": float(form.cleaned_data.get("area_y_percent") or 0),
                    "w_percent": float(form.cleaned_data.get("area_w_percent") or 100),
                    "h_percent": float(form.cleaned_data.get("area_h_percent") or 100),
                },
                "zonas_texto_custom": form.cleaned_data.get("custom_text_zones") or [],
                "preview_mode": True,
            },
        }
        analise.save()
        executar_analise_imagem(analise)
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
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
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
        zona_relatorio = _parse_zone_payload(report_zone, single=True)
        zonas_texto = _parse_zone_payload(custom_zones, single=False)
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "As zonas definidas são inválidas."}, status=400)

    preset, _created = AnaliseZonaPresetAI.objects.update_or_create(
        empresa=empresa,
        tipo_documento=tipo_documento,
        nome=nome,
        defaults={
            "zona_relatorio": zona_relatorio or {},
            "zonas_texto": zonas_texto or [],
            "criado_por": request.user,
        },
    )
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
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise = get_object_or_404(
        AnaliseImagemAI.objects.select_related("projeto", "furo", "criado_por").prefetch_related("deteccoes"),
        pk=pk,
        empresa=empresa,
    )
    resumo_validacao = _construir_resumo_validacao_analise(analise)
    sugestoes_reprocessamento = _construir_sugestoes_reprocessamento(analise, resumo_validacao)
    resumo_ai_relatorio = _construir_resumo_ai_relatorio(analise)
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
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise = get_object_or_404(AnaliseImagemAI, pk=pk, empresa=empresa)
    campos_extraidos = dict(analise.campos_extraidos or {})
    campos = list(campos_extraidos.get("campos") or [])
    corrigidos = 0

    for indice, campo in enumerate(campos):
        valor_validado = (request.POST.get(f"campo_validado_{indice}") or "").strip()
        campo["valor_validado"] = valor_validado
        campo["validado_utilizador"] = bool(valor_validado)
        if valor_validado:
            corrigidos += 1

    campos_extraidos["campos"] = campos
    campos_extraidos["tem_validacao_utilizador"] = corrigidos > 0
    analise.campos_extraidos = campos_extraidos
    analise.save(update_fields=["campos_extraidos", "atualizado_em"])
    messages.success(request, "As correções manuais da análise foram guardadas.")
    return redirect("inspecao_ai:analise_detail", pk=analise.pk)


@login_required
@admin_required
def analise_guardar(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise = get_object_or_404(AnaliseImagemAI, pk=pk, empresa=empresa)
    analise.guardada = True
    analise.metadados = {
        **(analise.metadados or {}),
        "opcoes_entrada": {
            **(((analise.metadados or {}).get("opcoes_entrada")) or {}),
            "preview_mode": False,
        },
    }
    analise.save(update_fields=["guardada", "metadados", "atualizado_em"])
    messages.success(request, "A análise foi guardada no histórico.")
    return redirect("inspecao_ai:analise_detail", pk=analise.pk)


@login_required
@admin_required
def analise_reprocessar(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_inspecao(request)
    if resposta_erro:
        return resposta_erro

    analise_origem = get_object_or_404(
        AnaliseImagemAI.objects.select_related("projeto", "furo", "criado_por"),
        pk=pk,
        empresa=empresa,
    )
    relatorio_focus = (request.POST.get("relatorio_focus") or "").strip()
    foco_labels = {
        "cabecalho": "Faixa superior impressa",
        "data": "Data",
        "turno": "Turno",
        "equipa": "Equipa",
        "observacoes": "Área central do relatório",
        "rodape": "Rodapé impresso",
    }
    sufixo_nome = foco_labels.get(relatorio_focus, "reprocessada")
    nome_base = _nome_base_analise_reprocessada(analise_origem.nome)

    nova_analise = AnaliseImagemAI(
        empresa=empresa,
        projeto=analise_origem.projeto,
        furo=analise_origem.furo,
        criado_por=request.user,
        nome=f"{nome_base} · {sufixo_nome}",
        tipo_documento=analise_origem.tipo_documento,
        estado="pendente",
        guardada=False,
        marcador_predominante="indefinido",
        motor_analise=analise_origem.motor_analise,
        observacoes=analise_origem.observacoes,
        metadados={
            **(analise_origem.metadados or {}),
            "opcoes_entrada": {
                **(((analise_origem.metadados or {}).get("opcoes_entrada")) or {}),
                "relatorio_focus": relatorio_focus,
                "preview_mode": True,
            },
            "reprocessada_de": str(analise_origem.pk),
        },
    )

    if analise_origem.imagem_original:
        analise_origem.imagem_original.open("rb")
        try:
            conteudo = analise_origem.imagem_original.read()
        finally:
            analise_origem.imagem_original.close()
        nome_original = (analise_origem.imagem_original.name or "").split("/")[-1] or f"{analise_origem.pk}.jpg"
        nova_analise.imagem_original.save(nome_original, ContentFile(conteudo), save=False)

    nova_analise.save()

    executar_analise_imagem(nova_analise)
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
                resumo_contexto["memoria_furo_contexto"] = construir_memoria_operacional_furo(furo_contexto)
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
