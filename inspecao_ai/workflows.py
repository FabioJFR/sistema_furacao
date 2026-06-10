from pathlib import Path

from django.contrib import messages
from django.core.files.base import ContentFile
from django.shortcuts import redirect

from .domain_logic import (
    construir_memoria_operacional_furo,
    nome_base_analise_reprocessada,
    normalizar_nome_documento,
    parse_zone_payload,
    resolver_path_unico,
)
from .models import AnaliseImagemAI
from .selectors.access import (
    obter_empresa_inspecao_por_id,
    obter_perfil_admin_inspecao,
    obter_primeira_empresa_inspecao,
)
from .selectors.memoria import aplicar_filtros_memoria_qs, listar_furos_memoria_operacional_qs
from .services.presets import guardar_preset_zonas_service
from .services.training_examples import sincronizar_exemplos_validacao
from .services import executar_analise_imagem


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


def obter_empresa_admin_inspecao(request):
    if request.user.is_superuser:
        empresa_id = (request.GET.get("empresa") or request.POST.get("empresa") or "").strip()
        if empresa_id:
            empresa = obter_empresa_inspecao_por_id(empresa_id)
            if empresa:
                return empresa, None
        empresa = obter_primeira_empresa_inspecao()
        if empresa:
            return empresa, None
        messages.error(request, "Ainda não existe nenhuma empresa disponível para abrir a área de inspeção AI.")
        return None, redirect("plataforma:dashboard")

    perfil = obter_perfil_admin_inspecao(request.user)
    if not perfil or not perfil.empresa_id:
        messages.error(request, "Não tens permissão para aceder à área de inspeção AI.")
        return None, redirect("projetos:redirect_after_login")
    return perfil.empresa, None


def listar_documentos_biblioteca_base_conhecimento():
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


def guardar_documento_biblioteca(ficheiro):
    biblioteca_dir = KNOWLEDGE_BASE_ROOT / "pdf"
    biblioteca_dir.mkdir(parents=True, exist_ok=True)

    base_nome, extensao = normalizar_nome_documento(ficheiro.name)
    if not extensao:
        raise ValueError("O ficheiro precisa de ter uma extensão reconhecível.")
    if extensao not in EXTENSOES_BIBLIOTECA_PERMITIDAS:
        raise ValueError(f"A extensão {extensao} não está permitida nesta biblioteca.")

    destino = resolver_path_unico(biblioteca_dir, base_nome, extensao)
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
    return destino, txt_criado


def aplicar_filtros_memoria_operacional(empresa, termo, estado, com_coordenadas, despesas_altas, ordenar):
    furos_qs = aplicar_filtros_memoria_qs(
        listar_furos_memoria_operacional_qs(empresa),
        termo=termo,
        estado=estado,
        com_coordenadas=com_coordenadas,
        despesas_altas=despesas_altas,
    )

    ordenacao_map = {
        "recentes": ("-data",),
        "profundos": ("-profundidade_maxima_atingida", "-data"),
        "caros": ("-total_despesas_diretas", "-data"),
        "medicoes": ("-total_medicoes_registadas", "-data"),
    }
    furos = list(furos_qs.order_by(*ordenacao_map.get(ordenar, ("-data",)))[:24])
    return furos, [construir_memoria_operacional_furo(furo) for furo in furos]


def criar_analise_preview(form, empresa, user):
    analise = form.save(commit=False)
    analise.empresa = empresa
    analise.criado_por = user
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
    return analise


def guardar_preset_zonas(*, empresa, user, nome, tipo_documento, report_zone_raw, custom_zones_raw):
    zona_relatorio = parse_zone_payload(report_zone_raw, single=True)
    zonas_texto = parse_zone_payload(custom_zones_raw, single=False)
    preset = guardar_preset_zonas_service(
        empresa=empresa,
        user=user,
        nome=nome,
        tipo_documento=tipo_documento,
        zona_relatorio=zona_relatorio,
        zonas_texto=zonas_texto,
    )
    return preset


def guardar_correcoes_campos(analise, request_post, utilizador=None):
    campos_extraidos = dict(analise.campos_extraidos or {})
    campos = list(campos_extraidos.get("campos") or [])
    corrigidos = 0
    for indice, campo in enumerate(campos):
        valor_validado = (request_post.get(f"campo_validado_{indice}") or "").strip()
        campo["valor_validado"] = valor_validado
        campo["validado_utilizador"] = bool(valor_validado)
        if valor_validado:
            corrigidos += 1
    campos_extraidos["campos"] = campos
    campos_extraidos["tem_validacao_utilizador"] = corrigidos > 0
    analise.campos_extraidos = campos_extraidos
    analise.save(update_fields=["campos_extraidos", "atualizado_em"])
    sincronizar_exemplos_validacao(analise=analise, campos=campos, utilizador=utilizador)
    return analise


def guardar_analise_no_historico(analise):
    analise.guardada = True
    analise.metadados = {
        **(analise.metadados or {}),
        "opcoes_entrada": {
            **(((analise.metadados or {}).get("opcoes_entrada")) or {}),
            "preview_mode": False,
        },
    }
    analise.save(update_fields=["guardada", "metadados", "atualizado_em"])
    return analise


def reprocessar_analise(analise_origem, user, relatorio_focus):
    foco_labels = {
        "cabecalho": "Faixa superior impressa",
        "data": "Data",
        "turno": "Turno",
        "equipa": "Equipa",
        "observacoes": "Área central do relatório",
        "rodape": "Rodapé impresso",
    }
    sufixo_nome = foco_labels.get(relatorio_focus, "reprocessada")
    nome_base = nome_base_analise_reprocessada(analise_origem.nome)
    nova_analise = AnaliseImagemAI(
        empresa=analise_origem.empresa,
        projeto=analise_origem.projeto,
        furo=analise_origem.furo,
        criado_por=user,
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
    return nova_analise, foco_labels
