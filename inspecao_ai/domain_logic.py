import re
import json
from pathlib import Path

from django.utils.text import slugify

def normalizar_valor_comparacao_ai(valor):
    texto = (valor or "").strip().lower()
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.replace("ã", "a").replace("á", "a").replace("à", "a").replace("â", "a")
    texto = texto.replace("é", "e").replace("ê", "e")
    texto = texto.replace("í", "i")
    texto = texto.replace("ó", "o").replace("ô", "o").replace("õ", "o")
    texto = texto.replace("ú", "u")
    texto = re.sub(r"[^a-z0-9./:,\- ]", "", texto)
    return texto.strip()


def nome_base_analise_reprocessada(nome):
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


def parse_zone_payload(raw_value, *, single):
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


def normalizar_nome_documento(nome_original):
    path = Path(nome_original or "")
    extensao = path.suffix.lower().strip()
    base = slugify(path.stem or "")
    if not base:
        base = "documento"
    return base, extensao


def resolver_path_unico(base_dir, base_nome, extensao):
    candidato = base_dir / f"{base_nome}{extensao}"
    indice = 2
    while candidato.exists():
        candidato = base_dir / f"{base_nome}-{indice}{extensao}"
        indice += 1
    return candidato


def construir_resumo_validacao_analise(analise):
    campos = list(((analise.campos_extraidos or {}).get("campos") or []))
    total_validados = 0
    total_acertos = 0
    total_falhas = 0

    for campo in campos:
        valor_lido = (
            campo.get("valor_validado")
            if campo.get("validado_utilizador") and campo.get("valor_validado")
            else campo.get("valor_lido")
        )
        campo["valor_validado"] = campo.get("valor_validado") or ""
        campo["comparacao_estado"] = "sem_validacao"
        campo["comparacao_label"] = "Sem validação"

        if not campo.get("validado_utilizador") or not campo.get("valor_validado"):
            continue

        total_validados += 1
        valor_ai = normalizar_valor_comparacao_ai(campo.get("valor_lido"))
        valor_validado = normalizar_valor_comparacao_ai(campo.get("valor_validado"))

        if valor_ai and valor_ai == valor_validado:
            campo["comparacao_estado"] = "acertou"
            campo["comparacao_label"] = "AI acertou"
            total_acertos += 1
        else:
            campo["comparacao_estado"] = "falhou"
            campo["comparacao_label"] = "AI falhou"
            total_falhas += 1

        campo["valor_para_comparacao"] = valor_lido

    taxa_acerto = round((total_acertos / total_validados) * 100, 1) if total_validados else None
    return {
        "campos": campos,
        "total_validados": total_validados,
        "total_acertos": total_acertos,
        "total_falhas": total_falhas,
        "taxa_acerto": taxa_acerto,
    }


def construir_sugestoes_reprocessamento(analise, resumo_validacao):
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
        sugestoes.append({"focus": focus, "label": label, "reason": reason})

    if not sugestoes and resumo_validacao["total_falhas"] > 0:
        sugestoes.append(
            {
                "focus": "",
                "label": "Reanalisar relatório completo",
                "reason": "Existem falhas validadas, mas sem um campo semântico claro para isolar a próxima tentativa.",
            }
        )

    return sugestoes


def construir_resumo_ai_relatorio(analise):
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


def construir_dashboard_aprendizagem_ai(analises):
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

            valor_ai = normalizar_valor_comparacao_ai(campo.get("valor_lido"))
            valor_validado = normalizar_valor_comparacao_ai(campo.get("valor_validado"))
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


def filtrar_analises_visiveis(analises):
    resultado = []
    for analise in analises:
        opcoes = ((analise.metadados or {}).get("opcoes_entrada") or {})
        preview_mode = bool(opcoes.get("preview_mode"))
        if preview_mode and not analise.guardada:
            continue
        resultado.append(analise)
    return resultado


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

    texto_memoria = [f"Furo: {resumo['nome']}"]
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
        texto_memoria.append(f"Coordenadas: {resumo['latitude']}, {resumo['longitude']}")
    if resumo["observacoes"]:
        texto_memoria.append(f"Observações: {resumo['observacoes']}")

    resumo["texto_memoria"] = " | ".join(texto_memoria)
    return resumo
