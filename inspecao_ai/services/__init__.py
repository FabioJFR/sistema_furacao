from io import BytesIO
import re

from django.core.files.base import ContentFile
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from inspecao_ai.models import DeteccaoImagemAI


OCR_TEMPLATE_CHARS = "0123456789mM-./:,%º°HQNBPSS"
OCR_TEMPLATES = None


def _get_ocr_templates():
    global OCR_TEMPLATES
    if OCR_TEMPLATES is not None:
        return OCR_TEMPLATES

    templates = {}
    font = ImageFont.load_default()
    for char in OCR_TEMPLATE_CHARS:
        canvas = Image.new("L", (40, 40), 255)
        draw = ImageDraw.Draw(canvas)
        bbox = draw.textbbox((0, 0), char, font=font)
        text_w = max(1, bbox[2] - bbox[0])
        text_h = max(1, bbox[3] - bbox[1])
        x = (40 - text_w) // 2
        y = (40 - text_h) // 2
        draw.text((x, y), char, font=font, fill=0)
        binary = canvas.point(lambda px: 0 if px > 210 else 1, mode="1").convert("L")
        templates[char] = ImageOps.fit(binary, (24, 24), method=Image.Resampling.NEAREST)
    OCR_TEMPLATES = templates
    return OCR_TEMPLATES


def _simple_ocr_from_crop(imagem_crop, prepared=False):
    if imagem_crop is None:
        return {"text": "", "confidence": 0.0, "components": 0, "lines": 0}

    prepared_image = imagem_crop if prepared else _prepare_crop_for_ocr(imagem_crop)
    components = _find_connected_components(prepared_image)
    if not components:
        return {"text": "", "confidence": 0.0, "components": 0, "lines": 0}

    lines = _group_components_by_lines(components)
    templates = _get_ocr_templates()
    decoded_lines = []
    confidences = []

    for line in lines:
        chars = []
        line_conf = []
        for comp in line:
            char, conf = _decode_component(prepared_image, comp, templates)
            if char:
                chars.append((comp["bbox"][0], char))
                line_conf.append(conf)
        ordered = "".join(char for _, char in sorted(chars, key=lambda item: item[0])).strip()
        ordered = _cleanup_ocr_text(ordered)
        if ordered:
            decoded_lines.append(ordered)
            if line_conf:
                confidences.append(sum(line_conf) / len(line_conf))

    text = "\n".join(decoded_lines).strip()
    confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    return {
        "text": text,
        "confidence": confidence,
        "components": len(components),
        "lines": len(decoded_lines),
    }


def _prepare_crop_for_ocr(imagem_crop):
    gray = imagem_crop.convert("L")
    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    enlarged = gray.resize((max(32, gray.width * 3), max(32, gray.height * 3)), Image.Resampling.LANCZOS)
    binary = enlarged.point(lambda px: 0 if px > 180 else 255, mode="L")
    inverted = ImageChops.invert(binary)
    return inverted


def _prepare_crop_for_ocr_variants(imagem_crop):
    gray = imagem_crop.convert("L")
    gray = ImageOps.autocontrast(gray)
    enhanced = gray.filter(ImageFilter.MedianFilter(size=3))
    enhanced = enhanced.resize((max(32, gray.width * 3), max(32, gray.height * 3)), Image.Resampling.LANCZOS)

    variants = []
    for threshold, label in ((165, "claro"), (180, "base"), (195, "forte")):
        binary = enhanced.point(lambda px, limit=threshold: 0 if px > limit else 255, mode="L")
        variants.append({"label": label, "image": ImageChops.invert(binary)})

    contrasted = ImageOps.autocontrast(gray.point(lambda px: min(255, int(px * 1.1))))
    contrasted = contrasted.filter(ImageFilter.SHARPEN)
    contrasted = contrasted.resize((max(32, gray.width * 3), max(32, gray.height * 3)), Image.Resampling.LANCZOS)
    binary_contrasted = contrasted.point(lambda px: 0 if px > 176 else 255, mode="L")
    variants.append({"label": "contraste", "image": ImageChops.invert(binary_contrasted)})

    return variants


def _find_connected_components(binary_image):
    width, height = binary_image.size
    pixels = binary_image.load()
    visited = set()
    components = []

    for y in range(height):
        for x in range(width):
            if pixels[x, y] <= 0 or (x, y) in visited:
                continue
            stack = [(x, y)]
            visited.add((x, y))
            coords = []
            while stack:
                cx, cy = stack.pop()
                coords.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and pixels[nx, ny] > 0 and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        stack.append((nx, ny))

            if len(coords) < 14:
                continue
            xs = [item[0] for item in coords]
            ys = [item[1] for item in coords]
            bbox = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            if w < 3 or h < 5:
                continue
            components.append({"bbox": bbox, "pixels": len(coords), "width": w, "height": h})
    return components


def _group_components_by_lines(components):
    ordered = sorted(components, key=lambda item: (item["bbox"][1], item["bbox"][0]))
    lines = []
    for comp in ordered:
        cy = (comp["bbox"][1] + comp["bbox"][3]) / 2
        matched = False
        for line in lines:
            if abs(line["center_y"] - cy) <= max(10, comp["height"] * 0.7):
                line["items"].append(comp)
                centers = [((item["bbox"][1] + item["bbox"][3]) / 2) for item in line["items"]]
                line["center_y"] = sum(centers) / len(centers)
                matched = True
                break
        if not matched:
            lines.append({"center_y": cy, "items": [comp]})
    return [sorted(line["items"], key=lambda item: item["bbox"][0]) for line in lines]


def _decode_component(binary_image, component, templates):
    crop = binary_image.crop(component["bbox"])
    normalized = ImageOps.fit(crop, (24, 24), method=Image.Resampling.NEAREST)
    best_char = ""
    best_score = None
    total = 24 * 24 * 255
    for char, template in templates.items():
        diff = ImageChops.difference(normalized, template)
        score = 1.0 - (sum(diff.getdata()) / total)
        if best_score is None or score > best_score:
            best_score = score
            best_char = char

    if best_score is None or best_score < 0.42:
        return "", 0.0
    return best_char, round(best_score, 2)


def _cleanup_ocr_text(text):
    text = " ".join(text.replace("\n", " ").split())
    text = text.replace("MM", "M").replace("..", ".").replace("--", "-")
    return text.strip(" -")


def _extract_crop(image_rgb, bbox):
    x_min = max(0, int(bbox["x_min"]))
    y_min = max(0, int(bbox["y_min"]))
    x_max = min(image_rgb.width, int(bbox["x_max"]))
    y_max = min(image_rgb.height, int(bbox["y_max"]))
    if x_max <= x_min or y_max <= y_min:
        return None
    return image_rgb.crop((x_min, y_min, x_max, y_max))


def _safe_detection_text(value, max_length=240):
    text = (value or "").strip()
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 1].rstrip()}…"


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


def _extract_metric_value(text):
    if not text:
        return ""

    cleaned = text.strip().replace(" ", "")
    cleaned = cleaned.replace(",", ".")
    cleaned = re.sub(r"[^0-9mM./:-]", "", cleaned)
    cleaned = cleaned.replace("MM", "m").replace("M", "m")
    cleaned = cleaned.replace("..", ".").replace("--", "-")

    interval_match = re.search(r"(\d{1,3}(?:\.\d{1,2})?)-(\d{1,3}(?:\.\d{1,2})?)(m)?", cleaned)
    if interval_match:
        start = interval_match.group(1)
        end = interval_match.group(2)
        suffix = "m" if interval_match.group(3) or "m" in cleaned else ""
        return f"{start}-{end}{suffix}"

    meter_match = re.search(r"(\d{1,3}(?:\.\d{1,2})?)(m)?", cleaned)
    if meter_match:
        value = meter_match.group(1)
        suffix = "m" if meter_match.group(2) or "m" in cleaned else ""
        return f"{value}{suffix}"

    return ""


def _metric_numeric_value(metric_text):
    if not metric_text:
        return None
    match = re.search(r"(\d{1,3}(?:\.\d{1,2})?)", metric_text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _format_metric_number(value, with_suffix=False):
    if value is None:
        return ""
    if abs(value - round(value)) < 0.001:
        text = str(int(round(value)))
    else:
        text = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{text}m" if with_suffix else text


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


def _resolver_area_prioritaria_bbox(largura, altura, metadados):
    area = ((metadados or {}).get("opcoes_entrada", {}) or {}).get("area_prioritaria") or {}
    x_percent = float(area.get("x_percent") or 0)
    y_percent = float(area.get("y_percent") or 0)
    w_percent = float(area.get("w_percent") or 100)
    h_percent = float(area.get("h_percent") or 100)

    if x_percent <= 0 and y_percent <= 0 and w_percent >= 100 and h_percent >= 100:
        return None

    x_min = int(max(0.0, min(100.0, x_percent)) / 100.0 * largura)
    y_min = int(max(0.0, min(100.0, y_percent)) / 100.0 * altura)
    x_max = int(max(0.0, min(100.0, x_percent + w_percent)) / 100.0 * largura)
    y_max = int(max(0.0, min(100.0, y_percent + h_percent)) / 100.0 * altura)

    if x_max <= x_min or y_max <= y_min:
        return None
    return {"x_min": x_min, "y_min": y_min, "x_max": x_max, "y_max": y_max}


def _resolver_bbox_percentual(largura, altura, zone):
    if not zone:
        return None
    x_min = int(max(0.0, min(100.0, float(zone.get("x_percent") or 0))) / 100.0 * largura)
    y_min = int(max(0.0, min(100.0, float(zone.get("y_percent") or 0))) / 100.0 * altura)
    x_max = int(
        max(0.0, min(100.0, float(zone.get("x_percent") or 0) + float(zone.get("w_percent") or 0))) / 100.0 * largura
    )
    y_max = int(
        max(0.0, min(100.0, float(zone.get("y_percent") or 0) + float(zone.get("h_percent") or 0))) / 100.0 * altura
    )
    if x_max <= x_min or y_max <= y_min:
        return None
    return {"x_min": x_min, "y_min": y_min, "x_max": x_max, "y_max": y_max}


def _inferir_campo_semantico_custom(nome):
    texto = (nome or "").strip().lower()
    if "data" in texto:
        return "data"
    if "turno" in texto:
        return "turno"
    if "equipa" in texto or "operador" in texto:
        return "equipa"
    if "cliente" in texto:
        return "cliente"
    if "estaleiro" in texto:
        return "estaleiro"
    if "sond" in texto or "furo" in texto:
        return "sondagem_numero"
    if "inclina" in texto:
        return "inclinacao"
    if "perfil" in texto:
        return "perfil_furacao"
    if "inicio" in texto or "início" in texto:
        return "profundidade_inicio"
    if "final" in texto:
        return "profundidade_final"
    if "avan" in texto:
        return "avanco_turno"
    if "recuper" in texto and "%" in texto:
        return "recuperacao_percentual"
    if "recuper" in texto or "testemunho" in texto:
        return "testemunho_recuperado"
    if "tempo" in texto or "hora" in texto:
        return "tempos"
    if "param" in texto:
        return "parametros"
    if "tarolo" in texto or "descr" in texto:
        return "furacao_tarolo"
    if "fur" in texto and "inicio" in texto:
        return "furacao_inicio"
    if "fur" in texto and "fim" in texto:
        return "furacao_fim"
    if "fur" in texto and "avan" in texto:
        return "furacao_avanco"
    if "assin" in texto or "nome" in texto:
        return "assinatura_equipa"
    return "observacoes"


def _construir_zonas_custom_relatorio(largura, altura, metadados):
    zonas_custom = []
    opcoes = ((metadados or {}).get("opcoes_entrada") or {})
    for index, zone in enumerate(opcoes.get("zonas_texto_custom") or [], start=1):
        bbox = _resolver_bbox_percentual(largura, altura, zone)
        if not bbox:
            continue
        nome = (zone.get("name") or "").strip() or f"Zona personalizada {index}"
        zonas_custom.append(
            {
                "rotulo": nome,
                "tipo_zona": "zona_custom_manual",
                "tipo_conteudo": "manual",
                "campo_semantico_base": _inferir_campo_semantico_custom(nome),
                **bbox,
            }
        )
    return zonas_custom


def _zona_intersecta_area(zona, area_bbox):
    if not area_bbox:
        return True

    zx1 = int(zona["x_min"])
    zy1 = int(zona["y_min"])
    zx2 = int(zona["x_max"])
    zy2 = int(zona["y_max"])
    ax1 = int(area_bbox["x_min"])
    ay1 = int(area_bbox["y_min"])
    ax2 = int(area_bbox["x_max"])
    ay2 = int(area_bbox["y_max"])

    inter_x1 = max(zx1, ax1)
    inter_y1 = max(zy1, ay1)
    inter_x2 = min(zx2, ax2)
    inter_y2 = min(zy2, ay2)
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        center_x = (zx1 + zx2) / 2
        center_y = (zy1 + zy2) / 2
        return ax1 <= center_x <= ax2 and ay1 <= center_y <= ay2

    zona_area = max(1, (zx2 - zx1) * (zy2 - zy1))
    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    return (inter_area / zona_area) >= 0.18


def _refinar_progressao_metricas_caixa(deteccoes_zonas):
    if not deteccoes_zonas:
        return deteccoes_zonas

    por_fila = {}
    for item in deteccoes_zonas:
        fila = item["metadados"].get("fila")
        por_fila.setdefault(fila, []).append(item)

    for fila, itens in por_fila.items():
        ordenados = sorted(itens, key=lambda det: det["bbox"]["x_min"])
        valores = []
        for det in ordenados:
            metric_text = det.get("valor_metrico_estimado") or det["metadados"].get("valor_metrico_estimado")
            valores.append(_metric_numeric_value(metric_text))

        passos = []
        for idx in range(1, len(valores)):
            prev_value = valores[idx - 1]
            current_value = valores[idx]
            if prev_value is None or current_value is None:
                continue
            delta = current_value - prev_value
            if 0.25 <= delta <= 6:
                passos.append(delta)

        passo_base = None
        if passos:
            passo_base = sorted(passos)[len(passos) // 2]

        if passo_base is None:
            continue

        for idx, det in enumerate(ordenados):
            atual = valores[idx]
            vizinho_esq = valores[idx - 1] if idx > 0 else None
            vizinho_dir = valores[idx + 1] if idx + 1 < len(valores) else None
            inferido = None

            if atual is None and vizinho_esq is not None:
                inferido = vizinho_esq + passo_base
            elif atual is None and vizinho_dir is not None:
                inferido = vizinho_dir - passo_base
            elif atual is not None and vizinho_esq is not None:
                esperado = vizinho_esq + passo_base
                if abs(atual - esperado) > max(1.5, passo_base * 1.4):
                    inferido = esperado
            elif atual is not None and vizinho_dir is not None:
                esperado = vizinho_dir - passo_base
                if abs(atual - esperado) > max(1.5, passo_base * 1.4):
                    inferido = esperado

            if inferido is None:
                continue

            metric_text_atual = det.get("valor_metrico_estimado") or det["metadados"].get("valor_metrico_estimado") or ""
            with_suffix = "m" in metric_text_atual.lower()
            texto_inferido = _format_metric_number(inferido, with_suffix=with_suffix)
            det["valor_metrico_estimado"] = texto_inferido
            det["texto_sugerido"] = texto_inferido
            det["metadados"]["valor_metrico_estimado"] = texto_inferido
            det["metadados"]["progressao_refinada"] = True
            det["metadados"]["passo_metrico_estimado"] = round(passo_base, 2)
            if atual is None:
                det["metadados"]["origem_valor_metrico"] = "inferido_por_progressao"
            else:
                det["metadados"]["origem_valor_metrico"] = "corrigido_por_progressao"

    ordenados_globais = sorted(
        deteccoes_zonas,
        key=lambda det: (det["metadados"].get("fila") or 0, det["bbox"]["x_min"]),
    )
    valores_globais = [
        _metric_numeric_value(det.get("valor_metrico_estimado") or det["metadados"].get("valor_metrico_estimado"))
        for det in ordenados_globais
    ]
    passos_globais = []
    for idx in range(1, len(valores_globais)):
        prev_value = valores_globais[idx - 1]
        current_value = valores_globais[idx]
        if prev_value is None or current_value is None:
            continue
        delta = current_value - prev_value
        if 0.25 <= delta <= 12:
            passos_globais.append(delta)

    if passos_globais:
        passo_global = sorted(passos_globais)[len(passos_globais) // 2]
        for idx, det in enumerate(ordenados_globais):
            atual = valores_globais[idx]
            prev_value = valores_globais[idx - 1] if idx > 0 else None
            next_value = valores_globais[idx + 1] if idx + 1 < len(valores_globais) else None
            inferido = None

            if atual is None and prev_value is not None:
                inferido = prev_value + passo_global
            elif atual is None and next_value is not None:
                inferido = next_value - passo_global

            if inferido is None:
                continue

            metric_text_atual = det.get("valor_metrico_estimado") or det["metadados"].get("valor_metrico_estimado") or ""
            with_suffix = "m" in metric_text_atual.lower()
            texto_inferido = _format_metric_number(inferido, with_suffix=with_suffix)
            det["valor_metrico_estimado"] = texto_inferido
            det["texto_sugerido"] = texto_inferido
            det["metadados"]["valor_metrico_estimado"] = texto_inferido
            det["metadados"]["progressao_refinada"] = True
            det["metadados"]["passo_metrico_estimado"] = round(passo_global, 2)
            det["metadados"]["origem_valor_metrico"] = "inferido_por_progressao_global"

    return deteccoes_zonas


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


def _zona_corresponde_focus_relatorio(zona, report_focus):
    focus = (report_focus or "").strip()
    if not focus:
        return True
    if focus == "cabecalho":
        return zona["tipo_zona"] == "cabecalho_impresso"
    if focus == "rodape":
        return zona["tipo_zona"] == "rodape_impresso"
    if focus == "observacoes":
        return zona["tipo_zona"] == "zona_central_manual"
    if focus in {"data", "turno", "equipa"}:
        return zona.get("campo_semantico_base") == focus
    return True


def _area_toca_topo_relatorio(area_bbox, altura):
    if not area_bbox:
        return False
    topo_limite = int(altura * 0.28)
    return int(area_bbox["y_min"]) < topo_limite and int(area_bbox["y_max"]) > int(topo_limite * 0.45)


def executar_analise_imagem(analise):
    if not analise.imagem_original:
        analise.estado = "erro"
        analise.erro_analise = "A análise não possui imagem original."
        analise.save(update_fields=["estado", "erro_analise", "atualizado_em"])
        return analise

    try:
        if analise.tipo_documento == "relatorio_trabalhador":
            return _analisar_relatorio(analise)
        return _analisar_caixa_cilindrica(analise)
    except Exception as exc:  # pragma: no cover - fallback defensivo
        analise.estado = "erro"
        analise.erro_analise = str(exc)
        analise.save(update_fields=["estado", "erro_analise", "atualizado_em"])
        return analise


def _analisar_relatorio(analise):
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


def _analisar_caixa_cilindrica(analise):
    with Image.open(analise.imagem_original) as imagem:
        imagem = imagem.convert("RGB")
        imagem.thumbnail((1800, 1800))
        imagem_corrigida, rotacao_aplicada, modo_rotacao = _corrigir_rotacao_caixa(imagem, analise.metadados or {})
        resultado = _executar_pipeline_caixa(imagem_corrigida, metadados=analise.metadados or {})

        analise.deteccoes.all().delete()
        imagem_processada = imagem_corrigida.copy()
        draw = ImageDraw.Draw(imagem_processada)
        _desenhar_guia_caixa(draw, largura=resultado["largura"], altura=resultado["altura"])

        maior_bbox = {}
        for indice, deteccao in enumerate(resultado["deteccoes_zonas"], start=1):
            bbox = deteccao["bbox"]
            cor = "#1d4ed8" if deteccao["marcador_cor"] == "azul" else "#111827"
            if deteccao["marcador_cor"] == "misto":
                cor = "#7c3aed"

            draw.rectangle(
                [(bbox["x_min"], bbox["y_min"]), (bbox["x_max"], bbox["y_max"])],
                outline=cor,
                width=5,
            )
            legenda_largura = min(resultado["largura"], bbox["x_min"] + 340)
            legenda_topo = max(0, bbox["y_min"] - 26)
            draw.rectangle(
                [(bbox["x_min"], legenda_topo), (legenda_largura, bbox["y_min"])],
                fill="#ffffff",
            )
            draw.text(
                (bbox["x_min"] + 6, legenda_topo + 4),
                f"{deteccao['rotulo']} | {deteccao['marcador_cor']} | {deteccao['confianca']:.2f}",
                fill=cor,
            )

            DeteccaoImagemAI.objects.create(
                analise=analise,
                ordem=indice,
                tipo_deteccao="texto_marcador",
                marcador_cor=deteccao["marcador_cor"],
                confianca=deteccao["confianca"],
                texto_sugerido=_safe_detection_text(deteccao["texto_sugerido"]),
                caixa_delimitadora=bbox,
                metadados=deteccao["metadados"],
            )
            if not maior_bbox:
                maior_bbox = bbox

        texto_detectado = bool(resultado["deteccoes_zonas"])
        confianca = resultado["confianca"]
        texto_sugerido_total = "\n".join(item["texto_sugerido"] for item in resultado["deteccoes_zonas"])

        buffer = BytesIO()
        imagem_processada.save(buffer, format="PNG")
        buffer.seek(0)
        nome_saida = f"{analise.pk}_processada.png"
        analise.imagem_processada.save(nome_saida, ContentFile(buffer.read()), save=False)

    analise.estado = "concluida" if texto_detectado else "revisao_manual"
    analise.texto_detectado = texto_detectado
    analise.marcador_predominante = resultado["marcador"]
    analise.confianca_media = confianca
    analise.texto_extraido_bruto = texto_sugerido_total
    analise.texto_normalizado = texto_sugerido_total
    analise.campos_extraidos = {
        "tipo_documento": "caixa_cilindrica",
        "campos": [
            {
                "campo": item["rotulo"],
                "tipo_zona": item["metadados"].get("tipo_zona"),
                "valor_metrico_estimado": item.get("valor_metrico_estimado"),
                "origem_valor_metrico": item["metadados"].get("origem_valor_metrico"),
                "passo_metrico_estimado": item["metadados"].get("passo_metrico_estimado"),
                "valor_lido": item["texto_sugerido"],
                "confianca": item["confianca"],
            }
            for item in resultado["deteccoes_zonas"]
        ],
    }
    analise.metadados = {
        "tipo_estrutura_caixa": "retangular_4_filas",
        "largura": resultado["largura"],
        "altura": resultado["altura"],
        "pixels_marcador": resultado["total_pontos"],
        "pixels_azul": resultado["pontos_azul"],
        "pixels_preto": resultado["pontos_preto"],
        "cobertura_marcador": round(resultado["cobertura"], 6),
        "zonas_analisadas": len(resultado["zonas"]),
        "deteccoes_encontradas": len(resultado["deteccoes_zonas"]),
        "area_prioritaria_bbox": resultado.get("area_prioritaria_bbox"),
        "bbox_principal": maior_bbox,
        "zonas_deteccao": [item["metadados"] for item in resultado["deteccoes_zonas"]],
        "rotacao_aplicada_graus": rotacao_aplicada,
        "modo_rotacao": modo_rotacao,
        "nota": (
            "Análise orientada à caixa testemunho com 4 filas. Foram avaliadas pontas e divisórias "
            "como zonas prioritárias para marcações de metros."
        ),
        "opcoes_entrada": (analise.metadados or {}).get("opcoes_entrada", {}),
    }
    analise.erro_analise = ""
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


def _executar_pipeline_caixa(imagem, metadados=None):
    largura, altura = imagem.size
    pixels = imagem.load()
    area_prioritaria = _resolver_area_prioritaria_bbox(largura, altura, metadados or {})
    pontos_marcador = []
    pontos_azul = 0
    pontos_preto = 0
    passo = 2 if max(largura, altura) > 1000 else 1

    for y in range(0, altura, passo):
        for x in range(0, largura, passo):
            r, g, b = pixels[x, y]
            if _eh_marcador_azul(r, g, b):
                pontos_azul += 1
                pontos_marcador.append((x, y))
            elif _eh_marcador_preto(r, g, b):
                pontos_preto += 1
                pontos_marcador.append((x, y))

    total_pixels_amostrados = max(1, (largura // passo) * (altura // passo))
    total_pontos = len(pontos_marcador)
    cobertura = total_pontos / total_pixels_amostrados
    marcador = _determinar_marcador(pontos_azul=pontos_azul, pontos_preto=pontos_preto)
    zonas = _construir_zonas_caixa(largura=largura, altura=altura)
    deteccoes_zonas = []
    for zona in zonas:
        if not _zona_intersecta_area(zona, area_prioritaria):
            continue
        deteccao = _avaliar_zona(
            pixels=pixels,
            largura=largura,
            altura=altura,
            passo=passo,
            zona=zona,
            image_rgb=imagem,
        )
        if deteccao:
            deteccoes_zonas.append(deteccao)

    deteccoes_zonas = _refinar_progressao_metricas_caixa(deteccoes_zonas)

    confianca = (
        round(sum(item["confianca"] for item in deteccoes_zonas) / len(deteccoes_zonas), 2)
        if deteccoes_zonas
        else 0.08
    )
    score = round((len(deteccoes_zonas) * 6) + (cobertura * 1000) + (confianca * 10), 4)

    return {
        "largura": largura,
        "altura": altura,
        "pontos_azul": pontos_azul,
        "pontos_preto": pontos_preto,
        "total_pontos": total_pontos,
        "cobertura": cobertura,
        "marcador": marcador,
        "area_prioritaria_bbox": area_prioritaria,
        "zonas": zonas,
        "deteccoes_zonas": deteccoes_zonas,
        "confianca": confianca,
        "score": score,
    }


def _corrigir_rotacao_caixa(imagem, metadados):
    opcoes = (metadados or {}).get("opcoes_entrada", {})
    rotacao_manual = float(opcoes.get("rotacao_manual_graus") or 0)
    auto_corrigir = bool(opcoes.get("auto_corrigir_inclinacao", True))

    if rotacao_manual:
        return (
            imagem.rotate(-rotacao_manual, expand=True, fillcolor="white"),
            rotacao_manual,
            "manual",
        )

    if not auto_corrigir:
        return imagem, 0.0, "sem_correcao"

    candidatos = [-12, -8, -4, 0, 4, 8, 12]
    melhor_imagem = imagem
    melhor_angulo = 0.0
    melhor_score = None
    for angulo in candidatos:
        candidata = imagem.rotate(-angulo, expand=True, fillcolor="white")
        resultado = _executar_pipeline_caixa(candidata)
        if melhor_score is None or resultado["score"] > melhor_score:
            melhor_imagem = candidata
            melhor_angulo = float(angulo)
            melhor_score = resultado["score"]

    return melhor_imagem, melhor_angulo, "automatico"


def _eh_marcador_azul(r, g, b):
    return b >= 70 and b > r * 1.18 and b > g * 1.08 and (b - r) >= 24


def _eh_marcador_preto(r, g, b):
    return max(r, g, b) <= 95 and (max(r, g, b) - min(r, g, b)) <= 28


def _construir_zonas_caixa(*, largura, altura):
    largura_ponta = max(48, int(largura * 0.12))
    largura_divisoria = max(34, int(largura * 0.06))
    largura_taco = max(28, int(largura * 0.045))
    fila_altura = altura / 4
    divisorias_x = [largura * 0.25, largura * 0.50, largura * 0.75]
    tacos_x = [largura * 0.16, largura * 0.38, largura * 0.62, largura * 0.84]
    zonas = []

    for indice_fila in range(4):
        y_min = int(indice_fila * fila_altura)
        y_max = int((indice_fila + 1) * fila_altura)
        linha = indice_fila + 1

        zonas.append(
            {
                "rotulo": f"Fila {linha} · ponta inicial",
                "tipo_zona": "ponta_inicial",
                "fila": linha,
                "x_min": 0,
                "x_max": largura_ponta,
                "y_min": y_min,
                "y_max": y_max,
            }
        )
        zonas.append(
            {
                "rotulo": f"Fila {linha} · ponta final",
                "tipo_zona": "ponta_final",
                "fila": linha,
                "x_min": largura - largura_ponta,
                "x_max": largura,
                "y_min": y_min,
                "y_max": y_max,
            }
        )

        for indice_div, divisoria_x in enumerate(divisorias_x, start=1):
            x_min = max(0, int(divisoria_x - largura_divisoria / 2))
            x_max = min(largura, int(divisoria_x + largura_divisoria / 2))
            zonas.append(
                {
                    "rotulo": f"Fila {linha} · divisória {indice_div}",
                    "tipo_zona": "divisoria",
                    "fila": linha,
                    "divisoria": indice_div,
                    "x_min": x_min,
                    "x_max": x_max,
                    "y_min": y_min,
                    "y_max": y_max,
                }
            )

        for indice_taco, taco_x in enumerate(tacos_x, start=1):
            x_min = max(0, int(taco_x - largura_taco / 2))
            x_max = min(largura, int(taco_x + largura_taco / 2))
            zonas.append(
                {
                    "rotulo": f"Fila {linha} · taco {indice_taco}",
                    "tipo_zona": "taco_madeira",
                    "fila": linha,
                    "taco": indice_taco,
                    "x_min": x_min,
                    "x_max": x_max,
                    "y_min": y_min,
                    "y_max": y_max,
                }
            )

    return zonas


def _avaliar_zona(*, pixels, largura, altura, passo, zona, image_rgb):
    x_min = max(0, int(zona["x_min"]))
    x_max = min(largura, int(zona["x_max"]))
    y_min = max(0, int(zona["y_min"]))
    y_max = min(altura, int(zona["y_max"]))

    pontos = []
    pontos_azul = 0
    pontos_preto = 0

    for y in range(y_min, y_max, passo):
        for x in range(x_min, x_max, passo):
            r, g, b = pixels[x, y]
            if _eh_marcador_azul(r, g, b):
                pontos_azul += 1
                pontos.append((x, y))
            elif _eh_marcador_preto(r, g, b):
                pontos_preto += 1
                pontos.append((x, y))

    total_pontos = len(pontos)
    area = max(1, ((x_max - x_min) // max(1, passo)) * ((y_max - y_min) // max(1, passo)))
    densidade = total_pontos / area
    limite_minimo = 16 if zona["tipo_zona"] in {"divisoria", "taco_madeira"} else 22
    if total_pontos < limite_minimo or densidade < 0.0012:
        return None

    marcador = _determinar_marcador(pontos_azul=pontos_azul, pontos_preto=pontos_preto)
    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    bbox = {
        "x_min": max(0, min(xs) - 10),
        "y_min": max(0, min(ys) - 10),
        "x_max": min(largura, max(xs) + 10),
        "y_max": min(altura, max(ys) + 10),
    }
    confianca = round(min(0.98, 0.30 + (densidade * 16) + (total_pontos / 800)), 2)
    ocr = _simple_ocr_from_crop(_extract_crop(image_rgb, bbox))
    valor_metrico_estimado = _extract_metric_value(ocr["text"])
    texto_sugerido = _texto_sugerido_zona(zona, ocr, valor_metrico_estimado)

    return {
        "rotulo": zona["rotulo"],
        "bbox": bbox,
        "marcador_cor": marcador,
        "confianca": confianca,
        "texto_sugerido": texto_sugerido,
        "valor_metrico_estimado": valor_metrico_estimado,
        "metadados": {
            "rotulo": zona["rotulo"],
            "tipo_zona": zona["tipo_zona"],
            "fila": zona["fila"],
            "divisoria": zona.get("divisoria"),
            "taco": zona.get("taco"),
            "densidade": round(densidade, 6),
            "pixels_azul": pontos_azul,
            "pixels_preto": pontos_preto,
            "pixels_totais": total_pontos,
            "texto_ocr_estimado": ocr["text"],
            "valor_metrico_estimado": valor_metrico_estimado,
            "ocr_confianca": ocr["confidence"],
            "ocr_componentes": ocr["components"],
            "ocr_linhas": ocr["lines"],
            "bbox": bbox,
        },
    }


def _texto_sugerido_zona(zona, ocr, valor_metrico_estimado):
    if valor_metrico_estimado:
        return valor_metrico_estimado

    texto_ocr = (ocr or {}).get("text", "").strip()
    if texto_ocr:
        return texto_ocr
    if zona["tipo_zona"] == "ponta_inicial":
        return f"Marcação de metros na ponta inicial da fila {zona['fila']}"
    if zona["tipo_zona"] == "ponta_final":
        return f"Marcação de metros na ponta final da fila {zona['fila']}"
    if zona["tipo_zona"] == "taco_madeira":
        return f"Marcação de metros no taco {zona.get('taco')} da fila {zona['fila']}"
    return f"Marcação de metros na divisória {zona.get('divisoria')} da fila {zona['fila']}"


def _desenhar_guia_caixa(draw, *, largura, altura):
    cor_guia = "#cbd5e1"
    cor_divisoria = "#94a3b8"
    fila_altura = altura / 4

    for indice in range(1, 4):
        y = int(indice * fila_altura)
        draw.line([(0, y), (largura, y)], fill=cor_guia, width=2)

    for proporcao in (0.25, 0.50, 0.75):
        x = int(largura * proporcao)
        draw.line([(x, 0), (x, altura)], fill=cor_divisoria, width=2)


def _determinar_marcador(*, pontos_azul, pontos_preto):
    if pontos_azul and pontos_preto:
        menor = min(pontos_azul, pontos_preto)
        maior = max(pontos_azul, pontos_preto)
        if menor / max(1, maior) >= 0.45:
            return "misto"
    if pontos_azul > pontos_preto:
        return "azul"
    if pontos_preto > pontos_azul:
        return "preto"
    return "indefinido"
