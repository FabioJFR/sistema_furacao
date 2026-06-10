from io import BytesIO
import re

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw

from inspecao_ai.models import DeteccaoImagemAI
from inspecao_ai.services.marker_colors import eh_marcador_azul as _eh_marcador_azul
from inspecao_ai.services.ocr_core import extract_crop as _extract_crop
from inspecao_ai.services.ocr_core import find_connected_components as _find_connected_components
from inspecao_ai.services.ocr_core import group_components_by_lines as _group_components_by_lines
from inspecao_ai.services.ocr_core import prepare_crop_for_ocr_variants as _prepare_crop_for_ocr_variants
from inspecao_ai.services.ocr_core import safe_detection_text as _safe_detection_text
from inspecao_ai.services.ocr_core import simple_ocr_from_crop as _simple_ocr_from_crop
from inspecao_ai.services.report_layout import area_toca_topo_relatorio as _area_toca_topo_relatorio
from inspecao_ai.services.report_layout import construir_zonas_custom_relatorio as _construir_zonas_custom_relatorio
from inspecao_ai.services.report_layout import resolver_bbox_percentual as _resolver_bbox_percentual
from inspecao_ai.services.report_layout import resolver_area_prioritaria_bbox as _resolver_area_prioritaria_bbox
from inspecao_ai.services.report_layout import zona_corresponde_focus_relatorio as _zona_corresponde_focus_relatorio
from inspecao_ai.services.report_layout import zona_intersecta_area as _zona_intersecta_area

def _normalize_short_field_text(text, semantic_field):
    normalized = _normalize_ocr_text(text).replace(" ", "")
    if not normalized:
        return ""

    replacements = {
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "|": "1",
        ",": ".",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)

    if semantic_field == "data":
        cleaned = re.sub(r"[^0-9./-]", "", normalized)
        digits = re.findall(r"\d+", cleaned)
        if len(digits) >= 3:
            joined = "".join(digits)
            if len(joined) >= 8:
                return f"{joined[:2]}/{joined[2:4]}/{joined[4:8]}"
        return cleaned

    if semantic_field == "inclinacao":
        cleaned = re.sub(r"[^0-9\-.,º°]", "", normalized)
        cleaned = cleaned.replace("..", ".")
        match = re.search(r"-?\d{1,3}(?:\.\d{1,2})?", cleaned)
        if match:
            suffix = "°" if ("º" in cleaned or "°" in cleaned) else ""
            return f"{match.group(0)}{suffix}"
        return cleaned

    if semantic_field in {"profundidade_inicio", "profundidade_final", "avanco_turno", "testemunho_recuperado"}:
        cleaned = re.sub(r"[^0-9.\-]", "", normalized)
        cleaned = cleaned.replace("..", ".")
        match = re.search(r"\d{1,4}(?:\.\d{1,2})?", cleaned)
        return match.group(0) if match else cleaned

    if semantic_field == "recuperacao_percentual":
        cleaned = re.sub(r"[^0-9.%]", "", normalized)
        cleaned = cleaned.replace("..", ".")
        match = re.search(r"\d{1,3}(?:\.\d{1,2})?", cleaned)
        if match:
            return f"{match.group(0)}%"
        return cleaned

    if semantic_field == "perfil_furacao":
        compact = re.sub(r"[^A-Za-z]", "", normalized).upper()
        for token in ("PQ", "HQ", "NQ", "BQ"):
            if token in compact:
                return token
        return compact[:4]

    if semantic_field == "sondagem_numero":
        cleaned = re.sub(r"[^A-Za-z0-9]", "", normalized).upper()
        match = re.search(r"[A-Z]{1,3}\d{2,8}", cleaned)
        return match.group(0) if match else cleaned

    return normalized


def _ocr_line_segments_from_prepared(prepared_image):
    components = _find_connected_components(prepared_image)
    if not components:
        return []

    segments = []
    for line in _group_components_by_lines(components):
        if not line:
            continue
        x_min = min(comp["bbox"][0] for comp in line)
        y_min = min(comp["bbox"][1] for comp in line)
        x_max = max(comp["bbox"][2] for comp in line)
        y_max = max(comp["bbox"][3] for comp in line)
        if (x_max - x_min) < 24 or (y_max - y_min) < 10:
            continue
        segments.append(
            {
                "bbox": (x_min, y_min, x_max, y_max),
                "componentes": len(line),
            }
        )
    return segments


def _best_ocr_for_observacoes_crop(imagem_crop):
    best = None
    for variant in _prepare_crop_for_ocr_variants(imagem_crop):
        prepared = variant["image"]
        segments = _ocr_line_segments_from_prepared(prepared)
        textos_linha = []
        confidences = []
        componentes_total = 0

        for segment in segments[:24]:
            crop = prepared.crop(segment["bbox"])
            line_ocr = _simple_ocr_from_crop(crop, prepared=True)
            line_quality = _report_ocr_quality(line_ocr["text"], "observacoes")
            line_profile = _ocr_text_profile(line_ocr["text"])
            if line_quality["usable"] or (
                line_profile["alpha_count"] >= 6
                and line_profile["alnum_ratio"] >= 0.62
                and line_profile["dominant_char_ratio"] <= 0.32
            ):
                textos_linha.append(_normalize_ocr_text(line_ocr["text"]))
                if line_ocr["confidence"]:
                    confidences.append(line_ocr["confidence"])
                componentes_total += segment["componentes"]

        joined = "\n".join(texto for texto in textos_linha if texto).strip()
        if not joined:
            fallback = _simple_ocr_from_crop(prepared, prepared=True)
            candidate = {
                **fallback,
                "variant": variant["label"],
                "line_mode": False,
                "quality": _report_ocr_quality(fallback["text"], "observacoes"),
                "score": round((fallback["confidence"] * 100), 2),
            }
        else:
            quality = _report_ocr_quality(joined, "observacoes")
            profile = _ocr_text_profile(joined)
            compact = profile["compact"].lower()
            if quality["usable"]:
                if (
                    profile["alpha_count"] < 14
                    or profile["alnum_ratio"] < 0.68
                    or profile["alpha_ratio"] < 0.38
                    or len(profile["word_like_tokens"]) < 3
                    or (compact.count("m") / max(1, len(compact))) > 0.34
                ):
                    quality = {"usable": False, "reason": "observacoes_ruidosas"}
            score = 0.0
            score += (sum(confidences) / len(confidences)) * 100 if confidences else 45
            score += min(profile["alpha_count"], 40) * 0.8
            score += min(len(profile["word_like_tokens"]), 10) * 6
            score -= max(0.0, profile["dominant_char_ratio"] - 0.24) * 35
            if quality["usable"]:
                score += 50
            candidate = {
                "text": joined,
                "confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
                "components": componentes_total,
                "lines": len(textos_linha),
                "variant": variant["label"],
                "line_mode": True,
                "quality": quality,
                "score": round(score, 2),
            }

        if best is None or candidate["score"] > best["score"]:
            best = candidate

    return best or {"text": "", "confidence": 0.0, "components": 0, "lines": 0, "variant": "none"}


def _best_ocr_for_report_crop(imagem_crop, semantic_field):
    if imagem_crop is None:
        return {"text": "", "confidence": 0.0, "components": 0, "lines": 0, "variant": "none"}

    if semantic_field == "observacoes":
        return _best_ocr_for_observacoes_crop(imagem_crop)

    short_field_semantics = {
        "data",
        "inclinacao",
        "profundidade_inicio",
        "profundidade_final",
        "avanco_turno",
        "testemunho_recuperado",
        "recuperacao_percentual",
        "perfil_furacao",
        "sondagem_numero",
    }

    best = None
    for variant in _prepare_crop_for_ocr_variants(imagem_crop):
        ocr = _simple_ocr_from_crop(variant["image"], prepared=True)
        if semantic_field in short_field_semantics:
            ocr["text"] = _normalize_short_field_text(ocr["text"], semantic_field)
        quality = _report_ocr_quality(ocr["text"], semantic_field)
        profile = _ocr_text_profile(ocr["text"])
        score = 0.0
        score += ocr["confidence"] * 100
        score += min(profile["alnum_ratio"], 1.0) * 20
        score += min(len(profile["word_like_tokens"]), 6) * 4
        score -= max(0.0, profile["dominant_char_ratio"] - 0.24) * 35
        if quality["usable"]:
            score += 40

        candidate = {
            **ocr,
            "variant": variant["label"],
            "quality": quality,
            "score": round(score, 2),
        }
        if best is None or candidate["score"] > best["score"]:
            best = candidate

    return best or {"text": "", "confidence": 0.0, "components": 0, "lines": 0, "variant": "none"}


def _normalize_ocr_text(text):
    return " ".join((text or "").strip().split())


def _ocr_text_profile(text):
    normalized = _normalize_ocr_text(text)
    visible = [char for char in normalized if not char.isspace()]
    if not visible:
        return {
            "normalized": "",
            "visible_len": 0,
            "alpha_count": 0,
            "digit_count": 0,
            "punct_count": 0,
            "alnum_ratio": 0.0,
            "alpha_ratio": 0.0,
            "digit_ratio": 0.0,
            "dominant_char_ratio": 0.0,
            "word_like_tokens": [],
            "compact": "",
        }

    alpha_count = sum(1 for char in visible if re.match(r"[A-Za-zÀ-ÿ]", char))
    digit_count = sum(1 for char in visible if char.isdigit())
    punct_count = len(visible) - alpha_count - digit_count
    compact = "".join(char for char in visible if char.isalnum())

    counts = {}
    for char in visible:
        counts[char] = counts.get(char, 0) + 1

    tokens = [token for token in re.split(r"\s+", normalized) if token]
    word_like_tokens = []
    for token in tokens:
        token_letters = len(re.findall(r"[A-Za-zÀ-ÿ]", token))
        token_digits = len(re.findall(r"\d", token))
        token_compact = re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", token)
        if token_letters >= 3 and len(token_compact) >= 3:
            word_like_tokens.append(token)
        elif token_letters >= 2 and token_digits >= 1 and len(token_compact) >= 4:
            word_like_tokens.append(token)

    visible_len = len(visible)
    return {
        "normalized": normalized,
        "visible_len": visible_len,
        "alpha_count": alpha_count,
        "digit_count": digit_count,
        "punct_count": punct_count,
        "alnum_ratio": (alpha_count + digit_count) / visible_len,
        "alpha_ratio": alpha_count / visible_len,
        "digit_ratio": digit_count / visible_len,
        "dominant_char_ratio": max(counts.values()) / visible_len,
        "word_like_tokens": word_like_tokens,
        "compact": compact,
    }


def _ocr_text_is_noisy(profile):
    compact = profile["compact"]
    if not compact:
        return True
    if profile["alnum_ratio"] < 0.55:
        return True
    if profile["dominant_char_ratio"] > 0.38:
        return True
    if len(compact) >= 6 and len(set(compact.lower())) <= 2:
        return True
    return False


def _profile_repeated_symbol_noise(profile, allowed_chars):
    compact = profile["compact"]
    if not compact:
        return True
    normalized = compact.upper()
    filtered = "".join(char for char in normalized if char not in allowed_chars)
    if filtered:
        return False
    unique = {char for char in normalized if char.strip()}
    return len(unique) <= 3


def _report_ocr_quality(text, semantic_field):
    profile = _ocr_text_profile(text)
    normalized = profile["normalized"]
    if not normalized:
        return {"usable": False, "reason": "sem_texto"}
    if _ocr_text_is_noisy(profile):
        return {"usable": False, "reason": "ocr_ruidoso"}

    if semantic_field == "data":
        if re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}\.\d{1,2}\.\d{2,4}\b", normalized):
            return {"usable": True, "reason": "data_valida"}
        return {"usable": False, "reason": "data_invalida"}

    if semantic_field == "turno":
        lowered = normalized.lower()
        if any(token in lowered for token in ("manha", "manhã", "tarde", "noite", "turno")):
            return {"usable": True, "reason": "turno_reconhecido"}
        return {"usable": False, "reason": "turno_invalido"}

    if semantic_field == "equipa":
        if len(profile["word_like_tokens"]) >= 1 and profile["alpha_count"] >= 5 and profile["alnum_ratio"] >= 0.72:
            return {"usable": True, "reason": "equipa_parcial"}
        return {"usable": False, "reason": "equipa_invalida"}

    if semantic_field in {"cliente", "estaleiro", "parametros", "assinatura_equipa"}:
        if (
            len(profile["word_like_tokens"]) >= 1
            and profile["alpha_count"] >= 5
            and profile["alnum_ratio"] >= 0.72
            and profile["dominant_char_ratio"] <= 0.28
            and len(set(profile["compact"].lower())) >= 4
            and not _profile_repeated_symbol_noise(profile, {"N", "M", "%", "º", "°", ".", ",", "/", "-", ":"})
        ):
            return {"usable": True, "reason": "campo_textual_parcial"}
        return {"usable": False, "reason": "campo_textual_invalido"}

    if semantic_field == "sondagem_numero":
        compact = re.sub(r"[^A-Z0-9]", "", normalized.upper())
        if re.fullmatch(r"[A-Z]{1,3}\d{3,8}", compact):
            return {"usable": True, "reason": "sondagem_parcial"}
        return {"usable": False, "reason": "sondagem_invalida"}

    if semantic_field == "inclinacao":
        if re.fullmatch(r"-?\d{1,3}(?:[.,]\d{1,2})?\s*[º°]?", normalized):
            return {"usable": True, "reason": "inclinacao_parcial"}
        return {"usable": False, "reason": "inclinacao_invalida"}

    if semantic_field == "perfil_furacao":
        if re.fullmatch(r"(?:PQ|HQ|NQ|BQ)", normalized.upper()):
            return {"usable": True, "reason": "perfil_reconhecido"}
        return {"usable": False, "reason": "perfil_invalido"}

    if semantic_field in {"profundidade_inicio", "profundidade_final", "avanco_turno", "testemunho_recuperado"}:
        if re.fullmatch(r"\d{1,4}(?:[.,]\d{1,2})?", normalized):
            return {"usable": True, "reason": "valor_metrico_parcial"}
        return {"usable": False, "reason": "valor_metrico_invalido"}

    if semantic_field == "recuperacao_percentual":
        if re.fullmatch(r"\d{1,3}(?:[.,]\d{1,2})?\s*%", normalized):
            return {"usable": True, "reason": "percentagem_parcial"}
        return {"usable": False, "reason": "percentagem_invalida"}

    if semantic_field == "tempos":
        if re.search(r"\d{1,2}[:.]\d{2}", normalized):
            return {"usable": True, "reason": "tempos_parciais"}
        return {"usable": False, "reason": "tempos_invalidos"}

    if semantic_field == "furacao_registo":
        if len(re.findall(r"\d{1,4}(?:[.,]\d{1,2})?", normalized)) >= 2 and profile["alnum_ratio"] >= 0.68:
            return {"usable": True, "reason": "furacao_parcial"}
        return {"usable": False, "reason": "furacao_invalida"}

    if semantic_field in {"furacao_inicio", "furacao_fim", "furacao_avanco"}:
        if (
            re.fullmatch(r"\d{1,4}(?:[.,]\d{1,2})?", normalized)
            and profile["digit_count"] >= 2
            and not _profile_repeated_symbol_noise(profile, {"N", "M", "%", "º", "°", ".", ",", "/", "-", ":"})
        ):
            return {"usable": True, "reason": "furacao_parcial"}
        return {"usable": False, "reason": "furacao_invalida"}

    if semantic_field == "furacao_tarolo":
        if (
            len(profile["word_like_tokens"]) >= 1
            and profile["alpha_count"] >= 5
            and profile["alnum_ratio"] >= 0.7
            and profile["dominant_char_ratio"] <= 0.28
            and len(set(profile["compact"].lower())) >= 4
            and not _profile_repeated_symbol_noise(profile, {"N", "M", "%", "º", "°", ".", ",", "/", "-", ":"})
        ):
            return {"usable": True, "reason": "tarolo_parcial"}
        return {"usable": False, "reason": "tarolo_invalido"}

    if semantic_field == "identificacao_relatorio":
        if len(profile["compact"]) >= 7 and profile["alnum_ratio"] >= 0.75 and profile["dominant_char_ratio"] <= 0.28:
            return {"usable": True, "reason": "identificacao_parcial"}
        return {"usable": False, "reason": "identificacao_invalida"}

    if semantic_field == "observacoes":
        if (
            len(profile["word_like_tokens"]) >= 4
            and profile["alpha_count"] >= 12
            and profile["alnum_ratio"] >= 0.7
            and profile["alpha_ratio"] >= 0.45
        ):
            return {"usable": True, "reason": "observacoes_parciais"}
        return {"usable": False, "reason": "observacoes_ilegiveis"}

    if semantic_field == "rodape_validacao":
        if len(profile["compact"]) >= 5 and profile["alnum_ratio"] >= 0.75 and profile["dominant_char_ratio"] <= 0.3:
            return {"usable": True, "reason": "rodape_parcial"}
        return {"usable": False, "reason": "rodape_invalido"}

    if len(profile["compact"]) >= 5 and profile["alnum_ratio"] >= 0.72 and len(profile["word_like_tokens"]) >= 1:
        return {"usable": True, "reason": "generico_parcial"}
    return {"usable": False, "reason": "texto_nao_fiavel"}


def _fallback_report_value(zona, semantic_field, densidade_azul):
    if zona["tipo_zona"] == "cabecalho_impresso":
        return "Faixa superior impressa do relatório"
    if zona["tipo_zona"] == "campos_manuais_superiores":
        if semantic_field == "cliente":
            return "Área superior esquerda - Cliente"
        if semantic_field == "estaleiro":
            return "Área superior esquerda - Estaleiro"
        if semantic_field == "sondagem_numero":
            return "Área superior esquerda - Sondagem Nº"
        if semantic_field == "inclinacao":
            return "Área superior esquerda - Inclinação"
        if semantic_field == "perfil_furacao":
            return "Área superior esquerda - Perfil no turno"
        if semantic_field == "data":
            return "Área superior direita - Data"
        if semantic_field == "turno":
            return "Área superior direita - Turno"
        if semantic_field == "profundidade_inicio":
            return "Área superior direita - No início"
        if semantic_field == "profundidade_final":
            return "Área superior direita - No final"
        if semantic_field == "avanco_turno":
            return "Área superior direita - Avanço do turno"
        if semantic_field == "testemunho_recuperado":
            return "Área superior direita - Testemunho recuperado"
        if semantic_field == "recuperacao_percentual":
            return "Área superior direita - % de recuperação"
        if semantic_field == "equipa":
            return "Área superior manual do relatório - Equipa"
        if densidade_azul > 0.0015:
            return "Área superior manual com preenchimento do trabalhador"
        return "Área superior manual do relatório"
    if zona["tipo_zona"] == "zona_central_manual":
        if semantic_field == "tempos":
            return "Área central - coluna Tempos"
        if semantic_field == "parametros":
            return "Área central - coluna Parâmetros"
        if semantic_field == "furacao_inicio":
            return "Área central - Furação - Início"
        if semantic_field == "furacao_fim":
            return "Área central - Furação - Fim"
        if semantic_field == "furacao_avanco":
            return "Área central - Furação - Avanço"
        if semantic_field == "furacao_tarolo":
            return "Área central - Furação - Tarolo / descrição"
        if semantic_field == "furacao_registo":
            return "Área central - coluna Furação"
        if densidade_azul > 0.0015:
            return "Área central do relatório com escrita manual, mas ainda sem leitura fiável"
        return "Área central do relatório preparada para escrita manual"
    if zona["tipo_zona"] == "zona_inferior_manual":
        return "Zona inferior do relatório com nomes e assinatura do turno"
    if zona["tipo_zona"] == "zona_custom_manual":
        return f"{zona['rotulo']} com escrita detetada, mas ainda sem leitura fiável"
    return "Rodapé impresso do relatório"


def _infer_report_semantic_field(zona, text):
    if zona.get("campo_semantico_base"):
        return zona["campo_semantico_base"]
    normalized = (text or "").strip().lower()
    compact = normalized.replace(" ", "")
    if zona["tipo_zona"] == "cabecalho_impresso":
        return "identificacao_relatorio"
    if zona["tipo_zona"] == "rodape_impresso":
        return "rodape_validacao"
    if zona["tipo_zona"] == "zona_central_manual":
        return "observacoes"
    if re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", normalized) or re.search(r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b", normalized):
        return "data"
    if any(token in normalized for token in ("turno", "manha", "manhã", "tarde", "noite")):
        return "turno"
    if any(token in normalized for token in ("equipa", "equipe", "operador", "sondador", "ajudante")):
        return "equipa"
    if zona["tipo_zona"] == "campos_manuais_superiores":
        if compact and len(compact) <= 14 and re.search(r"\d", compact):
            return "data_ou_turno"
        return "campos_superiores"
    return "campo_livre"


def _format_report_value(zona, text, semantic_field, densidade_azul):
    texto_ocr = _normalize_ocr_text(text)
    qualidade = _report_ocr_quality(texto_ocr, semantic_field)
    if texto_ocr and qualidade["usable"]:
        if semantic_field == "data":
            match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}\.\d{1,2}\.\d{2,4}\b", texto_ocr)
            return match.group(0) if match else texto_ocr
        if semantic_field == "turno":
            lowered = texto_ocr.lower()
            if "manha" in lowered or "manhã" in lowered:
                return "Turno da manhã"
            if "tarde" in lowered:
                return "Turno da tarde"
            if "noite" in lowered:
                return "Turno da noite"
            return texto_ocr
        if semantic_field == "equipa":
            return texto_ocr
        if semantic_field == "observacoes":
            return texto_ocr
        return texto_ocr
    return _fallback_report_value(zona, semantic_field, densidade_azul)


def analisar_relatorio(analise):
    with Image.open(analise.imagem_original) as imagem:
        imagem = imagem.convert("RGB")
        imagem.thumbnail((1800, 1800))
        largura, altura = imagem.size
        opcoes_entrada = ((analise.metadados or {}).get("opcoes_entrada") or {})
        report_focus = (opcoes_entrada.get("relatorio_focus") or "").strip()
        imagem_corrigida, rotacao_aplicada, modo_rotacao = _corrigir_rotacao_relatorio(
            imagem,
            analise.metadados or {},
        )
        largura, altura = imagem_corrigida.size
        pixels = imagem_corrigida.load()
        area_prioritaria = _resolver_area_prioritaria_bbox(largura, altura, analise.metadados or {})
        zona_relatorio = _resolver_bbox_percentual(
            largura,
            altura,
            (((analise.metadados or {}).get("opcoes_entrada") or {}).get("zona_relatorio") or {}),
        )

    analise.deteccoes.all().delete()
    zonas = _construir_zonas_relatorio(largura=largura, altura=altura)
    zonas.extend(_construir_zonas_custom_relatorio(largura, altura, analise.metadados or {}))
    area_toca_topo = _area_toca_topo_relatorio(area_prioritaria, altura)
    deteccoes = []
    imagem_processada = imagem_corrigida.copy()
    draw = ImageDraw.Draw(imagem_processada)
    _desenhar_guia_relatorio(draw, largura=largura, altura=altura)

    if zona_relatorio:
        draw.rectangle(
            [(zona_relatorio["x_min"], zona_relatorio["y_min"]), (zona_relatorio["x_max"], zona_relatorio["y_max"])],
            outline="#0284c7",
            width=5,
        )

    for indice, zona in enumerate(zonas, start=1):
        if not _zona_corresponde_focus_relatorio(zona, report_focus):
            continue
        if zona_relatorio and not _zona_intersecta_area(zona, zona_relatorio):
            continue
        if not (
            _zona_intersecta_area(zona, area_prioritaria)
            or (
                area_toca_topo
                and zona["tipo_zona"] in {"cabecalho_impresso", "campos_manuais_superiores"}
            )
        ):
            continue
        deteccao = _avaliar_zona_relatorio(
            pixels=pixels,
            largura=largura,
            altura=altura,
            zona=zona,
            image_rgb=imagem_corrigida,
        )
        deteccoes.append(deteccao)

        bbox = deteccao["bbox"]
        cor = "#0f766e" if deteccao["tipo_conteudo"] == "impresso" else "#7c3aed"
        draw.rectangle(
            [(bbox["x_min"], bbox["y_min"]), (bbox["x_max"], bbox["y_max"])],
            outline=cor,
            width=4,
        )
        legenda_topo = max(0, bbox["y_min"] - 24)
        legenda_largura = min(largura, bbox["x_min"] + 320)
        draw.rectangle(
            [(bbox["x_min"], legenda_topo), (legenda_largura, bbox["y_min"])],
            fill="#ffffff",
        )
        draw.text(
            (bbox["x_min"] + 6, legenda_topo + 4),
            f"{deteccao['rotulo']} | {deteccao['tipo_conteudo']} | {deteccao['confianca']:.2f}",
            fill=cor,
        )

        DeteccaoImagemAI.objects.create(
            analise=analise,
            ordem=indice,
            tipo_deteccao="zona_interesse",
            marcador_cor="indefinido",
            confianca=deteccao["confianca"],
            texto_sugerido=_safe_detection_text(deteccao["valor_sugerido"]),
            caixa_delimitadora=bbox,
            metadados=deteccao["metadados"],
        )

    buffer = BytesIO()
    imagem_processada.save(buffer, format="PNG")
    buffer.seek(0)
    nome_saida = f"{analise.pk}_processada.png"
    analise.imagem_processada.save(nome_saida, ContentFile(buffer.read()), save=False)

    texto_sugerido_total = "\n".join(
        f"{item['rotulo']}: {item['valor_sugerido']}" for item in deteccoes if item["valor_sugerido"]
    )
    confianca_media = round(sum(item["confianca"] for item in deteccoes) / max(1, len(deteccoes)), 2)
    analise.metadados = {
        "largura": largura,
        "altura": altura,
        "tipo_pipeline": "relatorio_trabalhador_segmentado",
        "tipo_estrutura_relatorio": "topo_impresso_com_campos_manuais_corpo_manual_rodape_impresso",
        "area_prioritaria_bbox": area_prioritaria,
        "zona_relatorio_bbox": zona_relatorio,
        "rotacao_aplicada_graus": rotacao_aplicada,
        "modo_rotacao": modo_rotacao,
        "zonas_relatorio": [item["metadados"] for item in deteccoes],
        "campos_identificados": len(deteccoes),
        "nota": (
            "O relatório foi segmentado por cabeçalho, campos manuais superiores, zona central manuscrita "
            "e rodapé impresso. A leitura literal completa dos valores pode ser refinada numa fase OCR seguinte."
        ),
        "opcoes_entrada": opcoes_entrada,
    }
    analise.erro_analise = ""
    analise.estado = "concluida"
    analise.texto_detectado = True
    analise.marcador_predominante = "indefinido"
    analise.confianca_media = confianca_media
    analise.texto_extraido_bruto = texto_sugerido_total
    analise.texto_normalizado = texto_sugerido_total
    analise.campos_extraidos = {
        "tipo_documento": "relatorio_trabalhador",
        "campos": [
            {
                "campo": item["rotulo"],
                "campo_impresso": item.get("campo_impresso"),
                "campo_semantico": item.get("campo_semantico"),
                "tipo_conteudo": item["tipo_conteudo"],
                "ocr_aceite": item.get("ocr_aceite"),
                "valor_lido": item["valor_sugerido"],
                "valor_preenchido_trabalhador": item.get("valor_preenchido"),
                "confianca": item["confianca"],
            }
            for item in deteccoes
        ],
    }
    analise.save(
        update_fields=[
            "imagem_processada",
            "estado",
            "texto_detectado",
            "marcador_predominante",
            "confianca_media",
            "texto_extraido_bruto",
            "texto_normalizado",
            "campos_extraidos",
            "metadados",
            "erro_analise",
            "atualizado_em",
        ]
    )
    return analise


def _corrigir_rotacao_relatorio(imagem, metadados):
    opcoes = (metadados or {}).get("opcoes_entrada", {})
    rotacao_manual = float(opcoes.get("rotacao_manual_graus") or 0)
    auto_corrigir = bool(opcoes.get("auto_corrigir_inclinacao", True))

    if rotacao_manual:
        return imagem.rotate(-rotacao_manual, expand=True, fillcolor="white"), rotacao_manual, "manual"

    if not auto_corrigir:
        return imagem, 0.0, "sem_correcao"

    largura, altura = imagem.size
    if altura >= largura:
        return imagem, 0.0, "automatico"

    imagem_corrigida = imagem.rotate(-90, expand=True, fillcolor="white")
    return imagem_corrigida, 90.0, "automatico"


def _construir_zonas_relatorio(*, largura, altura):
    topo_h = int(altura * 0.28)
    corpo_h = int(altura * 0.52)
    rodape_h = altura - topo_h - corpo_h
    left_col_max = int(largura * 0.56)
    right_col_min = int(largura * 0.72)
    centro_left = int(largura * 0.05)
    centro_right = int(largura * 0.95)
    corpo_y_min = topo_h
    corpo_y_max = topo_h + corpo_h
    rodape_y_min = corpo_y_max

    def build_vertical_fields(x_min, x_max, y_min, y_max, fields):
        total_h = y_max - y_min
        row_h = max(24, total_h // max(1, len(fields)))
        zonas = []
        cursor = y_min
        for index, (label, semantic) in enumerate(fields):
            next_y = y_max if index == len(fields) - 1 else min(y_max, cursor + row_h)
            zonas.append(
                {
                    "rotulo": label,
                    "tipo_zona": "campos_manuais_superiores",
                    "campo_semantico_base": semantic,
                    "tipo_conteudo": "manual",
                    "x_min": x_min,
                    "x_max": x_max,
                    "y_min": cursor,
                    "y_max": next_y,
                }
            )
            cursor = next_y
        return zonas

    zonas = [
        {
            "rotulo": "Faixa superior impressa",
            "tipo_zona": "cabecalho_impresso",
            "tipo_conteudo": "impresso",
            "x_min": 0,
            "x_max": largura,
            "y_min": 0,
            "y_max": int(topo_h * 0.12),
        },
    ]

    zonas.extend(
        build_vertical_fields(
            0,
            left_col_max,
            int(topo_h * 0.12),
            topo_h,
            [
                ("Área superior esquerda - Cliente", "cliente"),
                ("Área superior esquerda - Estaleiro", "estaleiro"),
                ("Área superior esquerda - Sondagem Nº", "sondagem_numero"),
                ("Área superior esquerda - Inclinação", "inclinacao"),
                ("Área superior esquerda - Perfil no turno", "perfil_furacao"),
            ],
        )
    )
    zonas.extend(
        build_vertical_fields(
            right_col_min,
            largura,
            int(topo_h * 0.12),
            topo_h,
            [
                ("Área superior direita - Data", "data"),
                ("Área superior direita - Turno", "turno"),
                ("Área superior direita - No início", "profundidade_inicio"),
                ("Área superior direita - No final", "profundidade_final"),
                ("Área superior direita - Avanço do turno", "avanco_turno"),
                ("Área superior direita - Testemunho recuperado", "testemunho_recuperado"),
                ("Área superior direita - % de recuperação", "recuperacao_percentual"),
            ],
        )
    )

    tempos_max = centro_left + int((centro_right - centro_left) * 0.16)
    parametros_max = centro_left + int((centro_right - centro_left) * 0.42)
    furacao_max = centro_right
    furacao_col_w = furacao_max - parametros_max
    furacao_inicio_max = parametros_max + int(furacao_col_w * 0.18)
    furacao_fim_max = parametros_max + int(furacao_col_w * 0.36)
    furacao_avanco_max = parametros_max + int(furacao_col_w * 0.54)

    zonas.extend(
        [
            {
                "rotulo": "Área central - coluna Tempos",
                "tipo_zona": "zona_central_manual",
                "campo_semantico_base": "tempos",
                "tipo_conteudo": "manual",
                "x_min": centro_left,
                "x_max": tempos_max,
                "y_min": corpo_y_min,
                "y_max": corpo_y_max,
            },
            {
                "rotulo": "Área central - coluna Parâmetros",
                "tipo_zona": "zona_central_manual",
                "campo_semantico_base": "parametros",
                "tipo_conteudo": "manual",
                "x_min": tempos_max,
                "x_max": parametros_max,
                "y_min": corpo_y_min,
                "y_max": corpo_y_max,
            },
            {
                "rotulo": "Área central - Furação - Início",
                "tipo_zona": "zona_central_manual",
                "campo_semantico_base": "furacao_inicio",
                "tipo_conteudo": "manual",
                "x_min": parametros_max,
                "x_max": furacao_inicio_max,
                "y_min": corpo_y_min,
                "y_max": corpo_y_max,
            },
            {
                "rotulo": "Área central - Furação - Fim",
                "tipo_zona": "zona_central_manual",
                "campo_semantico_base": "furacao_fim",
                "tipo_conteudo": "manual",
                "x_min": furacao_inicio_max,
                "x_max": furacao_fim_max,
                "y_min": corpo_y_min,
                "y_max": corpo_y_max,
            },
            {
                "rotulo": "Área central - Furação - Avanço",
                "tipo_zona": "zona_central_manual",
                "campo_semantico_base": "furacao_avanco",
                "tipo_conteudo": "manual",
                "x_min": furacao_fim_max,
                "x_max": furacao_avanco_max,
                "y_min": corpo_y_min,
                "y_max": corpo_y_max,
            },
            {
                "rotulo": "Área central - Furação - Tarolo / descrição",
                "tipo_zona": "zona_central_manual",
                "campo_semantico_base": "furacao_tarolo",
                "tipo_conteudo": "manual",
                "x_min": furacao_avanco_max,
                "x_max": furacao_max,
                "y_min": corpo_y_min,
                "y_max": corpo_y_max,
            },
            {
                "rotulo": "Zona inferior do relatório - nomes e assinatura",
                "tipo_zona": "zona_inferior_manual",
                "campo_semantico_base": "assinatura_equipa",
                "tipo_conteudo": "manual",
                "x_min": 0,
                "x_max": largura,
                "y_min": rodape_y_min,
                "y_max": altura,
            },
        ]
    )

    zonas.append(
        {
            "rotulo": "Área central do relatório - Bloco 1",
            "tipo_zona": "zona_central_manual",
            "campo_semantico_base": "observacoes",
            "tipo_conteudo": "manual",
            "x_min": furacao_avanco_max,
            "x_max": furacao_max,
            "y_min": corpo_y_min,
            "y_max": corpo_y_max,
        },
    )
    zonas.append(
        {
            "rotulo": "Rodapé impresso do relatório",
            "tipo_zona": "rodape_impresso",
            "tipo_conteudo": "impresso",
            "x_min": 0,
            "x_max": largura,
            "y_min": altura - max(rodape_h // 3, 80),
            "y_max": altura,
        }
    )
    return zonas


def _avaliar_zona_relatorio(*, pixels, largura, altura, zona, image_rgb):
    x_min = max(0, int(zona["x_min"]))
    x_max = min(largura, int(zona["x_max"]))
    y_min = max(0, int(zona["y_min"]))
    y_max = min(altura, int(zona["y_max"]))
    passo = 2 if max(largura, altura) > 1200 else 1

    escuros = 0
    azuis = 0
    for y in range(y_min, y_max, passo):
        for x in range(x_min, x_max, passo):
            r, g, b = pixels[x, y]
            if _eh_marcador_azul(r, g, b):
                azuis += 1
            if max(r, g, b) <= 170:
                escuros += 1

    area = max(1, ((x_max - x_min) // max(1, passo)) * ((y_max - y_min) // max(1, passo)))
    densidade = escuros / area
    densidade_azul = azuis / area
    confianca = round(min(0.98, 0.35 + (densidade * 4.5) + (densidade_azul * 18)), 2)

    bbox = {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
    }
    crop = _extract_crop(image_rgb, bbox)
    semantic_base = zona.get("campo_semantico_base")
    semantic_hint = semantic_base or _infer_report_semantic_field(zona, "")
    ocr = _best_ocr_for_report_crop(crop, semantic_hint)
    campo_semantico = _infer_report_semantic_field(zona, ocr["text"])
    valor_sugerido = _valor_sugerido_relatorio(zona, densidade, densidade_azul, ocr, campo_semantico)
    qualidade_ocr = _report_ocr_quality(ocr["text"], campo_semantico)
    campo_impresso = _campo_impresso_relatorio(zona, campo_semantico)
    valor_preenchido = _valor_preenchido_trabalhador(zona, valor_sugerido, qualidade_ocr["usable"])
    return {
        "rotulo": zona["rotulo"],
        "tipo_conteudo": zona["tipo_conteudo"],
        "campo_semantico": campo_semantico,
        "confianca": confianca,
        "valor_sugerido": valor_sugerido,
        "campo_impresso": campo_impresso,
        "valor_preenchido": valor_preenchido,
        "ocr_aceite": qualidade_ocr["usable"],
        "bbox": bbox,
        "metadados": {
            "rotulo": zona["rotulo"],
            "tipo_zona": zona["tipo_zona"],
            "tipo_conteudo": zona["tipo_conteudo"],
            "campo_semantico": campo_semantico,
            "ocr_aceite": qualidade_ocr["usable"],
            "ocr_motivo": qualidade_ocr["reason"],
            "densidade_escura": round(densidade, 6),
            "densidade_azul": round(densidade_azul, 6),
            "campo_identificado": valor_sugerido,
            "campo_impresso": campo_impresso,
            "valor_preenchido_trabalhador": valor_preenchido,
            "texto_ocr_estimado": ocr["text"],
            "ocr_confianca": ocr["confidence"],
            "ocr_componentes": ocr["components"],
            "ocr_linhas": ocr["lines"],
            "ocr_variant": ocr.get("variant"),
            "ocr_line_mode": bool(ocr.get("line_mode")),
            "bbox": bbox,
        },
    }


def _valor_sugerido_relatorio(zona, densidade, densidade_azul, ocr, campo_semantico):
    del densidade
    texto_ocr = (ocr or {}).get("text", "").strip()
    return _format_report_value(zona, texto_ocr, campo_semantico, densidade_azul)


def _campo_impresso_relatorio(zona, campo_semantico):
    if zona["tipo_zona"] == "zona_custom_manual":
        return f"Zona personalizada: {zona['rotulo']}"
    if zona["tipo_zona"] == "cabecalho_impresso":
        return "Identificação impressa do relatório"
    if zona["tipo_zona"] == "rodape_impresso":
        return "Validação e notas impressas do rodapé"
    if zona["tipo_zona"] == "campos_manuais_superiores":
        if campo_semantico == "cliente":
            return "Campo impresso: Cliente"
        if campo_semantico == "estaleiro":
            return "Campo impresso: Estaleiro"
        if campo_semantico == "sondagem_numero":
            return "Campo impresso: Sondagem Nº"
        if campo_semantico == "inclinacao":
            return "Campo impresso: Inclinação"
        if campo_semantico == "perfil_furacao":
            return "Campo impresso: O perf. no turno"
        if campo_semantico == "data":
            return "Campo impresso: Data"
        if campo_semantico == "turno":
            return "Campo impresso: Turno"
        if campo_semantico == "profundidade_inicio":
            return "Campo impresso: No início"
        if campo_semantico == "profundidade_final":
            return "Campo impresso: No final"
        if campo_semantico == "avanco_turno":
            return "Campo impresso: Avanço do turno"
        if campo_semantico == "testemunho_recuperado":
            return "Campo impresso: Testemunho recuperado"
        if campo_semantico == "recuperacao_percentual":
            return "Campo impresso: % de recuperação"
        if campo_semantico == "equipa":
            return "Campo impresso: Equipa"
        return "Campo impresso superior do relatório"
    if zona["tipo_zona"] == "zona_central_manual":
        if campo_semantico == "tempos":
            return "Campo impresso: Tempos"
        if campo_semantico == "parametros":
            return "Campo impresso: Parâmetros"
        if campo_semantico == "furacao_inicio":
            return "Campo impresso: Furação - Início"
        if campo_semantico == "furacao_fim":
            return "Campo impresso: Furação - Fim"
        if campo_semantico == "furacao_avanco":
            return "Campo impresso: Furação - Avanço"
        if campo_semantico == "furacao_tarolo":
            return "Campo impresso: Furação - Tarolo / descrição"
        if campo_semantico == "furacao_registo":
            return "Campo impresso: Furação (Início / Fim / Avanço / Tarolo)"
        return "Campo impresso: Área central do relatório"
    if zona["tipo_zona"] == "zona_inferior_manual":
        return "Campo impresso: nomes e assinatura do turno"
    return "Campo impresso do relatório"


def _valor_preenchido_trabalhador(zona, valor_sugerido, ocr_aceite):
    if zona["tipo_zona"] == "zona_custom_manual":
        if ocr_aceite:
            return valor_sugerido
        return f"Texto detetado em {zona['rotulo']}, mas ainda sem leitura fiável"
    if zona["tipo_zona"] == "campos_manuais_superiores":
        if ocr_aceite:
            return valor_sugerido
        return "Preenchimento manual detetado, mas ainda sem leitura fiável"
    if zona["tipo_zona"] == "zona_central_manual":
        if ocr_aceite:
            return valor_sugerido
        return "Escrita manual detetada na área central, mas ainda sem leitura fiável"
    if zona["tipo_zona"] == "zona_inferior_manual":
        if ocr_aceite:
            return valor_sugerido
        return "Nomes e assinatura detetados, mas ainda sem leitura fiável"
    return valor_sugerido


def _desenhar_guia_relatorio(draw, *, largura, altura):
    topo_h = int(altura * 0.20)
    corpo_h = int(altura * 0.60)
    cor = "#94a3b8"
    draw.line([(0, topo_h), (largura, topo_h)], fill=cor, width=2)
    draw.line([(0, topo_h + corpo_h), (largura, topo_h + corpo_h)], fill=cor, width=2)
