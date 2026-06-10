from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw

from inspecao_ai.models import DeteccaoImagemAI
from inspecao_ai.services.box_metrics import refinar_progressao_metricas_caixa
from inspecao_ai.services.marker_colors import eh_marcador_azul, eh_marcador_preto
from inspecao_ai.services.ocr_core import (
    extract_crop,
    extract_metric_value,
    safe_detection_text,
    simple_ocr_from_crop,
)
from inspecao_ai.services.report_layout import resolver_area_prioritaria_bbox, zona_intersecta_area


def analisar_caixa_cilindrica(analise):
    with Image.open(analise.imagem_original) as imagem:
        imagem = imagem.convert("RGB")
        imagem.thumbnail((1800, 1800))
        imagem_corrigida, rotacao_aplicada, modo_rotacao = corrigir_rotacao_caixa(imagem, analise.metadados or {})
        resultado = executar_pipeline_caixa(imagem_corrigida, metadados=analise.metadados or {})

        analise.deteccoes.all().delete()
        imagem_processada = imagem_corrigida.copy()
        draw = ImageDraw.Draw(imagem_processada)
        desenhar_guia_caixa(draw, largura=resultado["largura"], altura=resultado["altura"])

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
                texto_sugerido=safe_detection_text(deteccao["texto_sugerido"]),
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


def executar_pipeline_caixa(imagem, metadados=None):
    largura, altura = imagem.size
    pixels = imagem.load()
    area_prioritaria = resolver_area_prioritaria_bbox(largura, altura, metadados or {})
    pontos_marcador = []
    pontos_azul = 0
    pontos_preto = 0
    passo = 2 if max(largura, altura) > 1000 else 1

    for y in range(0, altura, passo):
        for x in range(0, largura, passo):
            r, g, b = pixels[x, y]
            if eh_marcador_azul(r, g, b):
                pontos_azul += 1
                pontos_marcador.append((x, y))
            elif eh_marcador_preto(r, g, b):
                pontos_preto += 1
                pontos_marcador.append((x, y))

    total_pixels_amostrados = max(1, (largura // passo) * (altura // passo))
    total_pontos = len(pontos_marcador)
    cobertura = total_pontos / total_pixels_amostrados
    marcador = determinar_marcador(pontos_azul=pontos_azul, pontos_preto=pontos_preto)
    zonas = construir_zonas_caixa(largura=largura, altura=altura)
    deteccoes_zonas = []
    for zona in zonas:
        if not zona_intersecta_area(zona, area_prioritaria):
            continue
        deteccao = avaliar_zona(
            pixels=pixels,
            largura=largura,
            altura=altura,
            passo=passo,
            zona=zona,
            image_rgb=imagem,
        )
        if deteccao:
            deteccoes_zonas.append(deteccao)

    deteccoes_zonas = refinar_progressao_metricas_caixa(deteccoes_zonas)

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


def corrigir_rotacao_caixa(imagem, metadados):
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
        resultado = executar_pipeline_caixa(candidata)
        if melhor_score is None or resultado["score"] > melhor_score:
            melhor_imagem = candidata
            melhor_angulo = float(angulo)
            melhor_score = resultado["score"]

    return melhor_imagem, melhor_angulo, "automatico"


def construir_zonas_caixa(*, largura, altura):
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


def avaliar_zona(*, pixels, largura, altura, passo, zona, image_rgb):
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
            if eh_marcador_azul(r, g, b):
                pontos_azul += 1
                pontos.append((x, y))
            elif eh_marcador_preto(r, g, b):
                pontos_preto += 1
                pontos.append((x, y))

    total_pontos = len(pontos)
    area = max(1, ((x_max - x_min) // max(1, passo)) * ((y_max - y_min) // max(1, passo)))
    densidade = total_pontos / area
    limite_minimo = 16 if zona["tipo_zona"] in {"divisoria", "taco_madeira"} else 22
    if total_pontos < limite_minimo or densidade < 0.0012:
        return None

    marcador = determinar_marcador(pontos_azul=pontos_azul, pontos_preto=pontos_preto)
    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    bbox = {
        "x_min": max(0, min(xs) - 10),
        "y_min": max(0, min(ys) - 10),
        "x_max": min(largura, max(xs) + 10),
        "y_max": min(altura, max(ys) + 10),
    }
    confianca = round(min(0.98, 0.30 + (densidade * 16) + (total_pontos / 800)), 2)
    ocr = simple_ocr_from_crop(extract_crop(image_rgb, bbox))
    valor_metrico_estimado = extract_metric_value(ocr["text"])
    texto_sugerido = texto_sugerido_zona(zona, ocr, valor_metrico_estimado)

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


def texto_sugerido_zona(zona, ocr, valor_metrico_estimado):
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


def desenhar_guia_caixa(draw, *, largura, altura):
    cor_guia = "#cbd5e1"
    cor_divisoria = "#94a3b8"
    fila_altura = altura / 4

    for indice in range(1, 4):
        y = int(indice * fila_altura)
        draw.line([(0, y), (largura, y)], fill=cor_guia, width=2)

    for proporcao in (0.25, 0.50, 0.75):
        x = int(largura * proporcao)
        draw.line([(x, 0), (x, altura)], fill=cor_divisoria, width=2)


def determinar_marcador(*, pontos_azul, pontos_preto):
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
