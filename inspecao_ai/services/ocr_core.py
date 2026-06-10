import re

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps


OCR_TEMPLATE_CHARS = "0123456789mM-./:,%º°HQNBPSS"
OCR_TEMPLATES = None


def simple_ocr_from_crop(imagem_crop, prepared=False):
    if imagem_crop is None:
        return {"text": "", "confidence": 0.0, "components": 0, "lines": 0}

    prepared_image = imagem_crop if prepared else prepare_crop_for_ocr(imagem_crop)
    components = find_connected_components(prepared_image)
    if not components:
        return {"text": "", "confidence": 0.0, "components": 0, "lines": 0}

    lines = group_components_by_lines(components)
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


def prepare_crop_for_ocr(imagem_crop):
    gray = imagem_crop.convert("L")
    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    enlarged = gray.resize((max(32, gray.width * 3), max(32, gray.height * 3)), Image.Resampling.LANCZOS)
    binary = enlarged.point(lambda px: 0 if px > 180 else 255, mode="L")
    return ImageChops.invert(binary)


def prepare_crop_for_ocr_variants(imagem_crop):
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


def find_connected_components(binary_image):
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


def group_components_by_lines(components):
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


def extract_crop(image_rgb, bbox):
    x_min = max(0, int(bbox["x_min"]))
    y_min = max(0, int(bbox["y_min"]))
    x_max = min(image_rgb.width, int(bbox["x_max"]))
    y_max = min(image_rgb.height, int(bbox["y_max"]))
    if x_max <= x_min or y_max <= y_min:
        return None
    return image_rgb.crop((x_min, y_min, x_max, y_max))


def safe_detection_text(value, max_length=240):
    text = (value or "").strip()
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 1].rstrip()}…"


def extract_metric_value(text):
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
