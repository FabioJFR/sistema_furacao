def resolver_area_prioritaria_bbox(largura, altura, metadados):
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


def resolver_bbox_percentual(largura, altura, zone):
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


def inferir_campo_semantico_custom(nome):
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


def construir_zonas_custom_relatorio(largura, altura, metadados):
    zonas_custom = []
    opcoes = ((metadados or {}).get("opcoes_entrada") or {})
    for index, zone in enumerate(opcoes.get("zonas_texto_custom") or [], start=1):
        bbox = resolver_bbox_percentual(largura, altura, zone)
        if not bbox:
            continue
        nome = (zone.get("name") or "").strip() or f"Zona personalizada {index}"
        zonas_custom.append(
            {
                "rotulo": nome,
                "tipo_zona": "zona_custom_manual",
                "tipo_conteudo": "manual",
                "campo_semantico_base": inferir_campo_semantico_custom(nome),
                **bbox,
            }
        )
    return zonas_custom


def zona_intersecta_area(zona, area_bbox):
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


def zona_corresponde_focus_relatorio(zona, report_focus):
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


def area_toca_topo_relatorio(area_bbox, altura):
    if not area_bbox:
        return False
    topo_limite = int(altura * 0.28)
    return int(area_bbox["y_min"]) < topo_limite and int(area_bbox["y_max"]) > int(topo_limite * 0.45)
