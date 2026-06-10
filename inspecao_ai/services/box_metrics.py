import re


def refinar_progressao_metricas_caixa(deteccoes_zonas):
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
            valores.append(metric_numeric_value(metric_text))

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
            texto_inferido = format_metric_number(inferido, with_suffix=with_suffix)
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
        metric_numeric_value(det.get("valor_metrico_estimado") or det["metadados"].get("valor_metrico_estimado"))
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
            texto_inferido = format_metric_number(inferido, with_suffix=with_suffix)
            det["valor_metrico_estimado"] = texto_inferido
            det["texto_sugerido"] = texto_inferido
            det["metadados"]["valor_metrico_estimado"] = texto_inferido
            det["metadados"]["progressao_refinada"] = True
            det["metadados"]["passo_metrico_estimado"] = round(passo_global, 2)
            det["metadados"]["origem_valor_metrico"] = "inferido_por_progressao_global"

    return deteccoes_zonas


def metric_numeric_value(metric_text):
    if not metric_text:
        return None
    match = re.search(r"(\d{1,3}(?:\.\d{1,2})?)", metric_text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def format_metric_number(value, with_suffix=False):
    if value is None:
        return ""
    if abs(value - round(value)) < 0.001:
        text = str(int(round(value)))
    else:
        text = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{text}m" if with_suffix else text
