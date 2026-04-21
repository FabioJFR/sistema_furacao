import math


def _valor_medicao(medicao, campo_novo, campo_antigo):
    if hasattr(medicao, campo_novo):
        return getattr(medicao, campo_novo, None)
    return getattr(medicao, campo_antigo, None)


def calcular_trajetoria_min_curv(medicoes, origem=(0.0, 0.0, 0.0)):
    x = float(origem[0] or 0.0)
    y = float(origem[1] or 0.0)
    z = float(origem[2] or 0.0)

    pontos = [(x, y, z)]
    doglegs = [0.0]
    alertas = ["OK"]

    if not medicoes:
        return pontos, doglegs, alertas

    # -------------------------------------------------
    # 1) TROÇO ORIGEM -> PRIMEIRA MEDIÇÃO
    # -------------------------------------------------
    p0 = medicoes[0]
    md0 = float(_valor_medicao(p0, "profundidade_medida", "profundidade") or 0.0)

    if md0 > 0:
        inc0 = float(_valor_medicao(p0, "inclinacao_real_medida", "inclinacao") or 0.0)
        az0 = float(_valor_medicao(p0, "azimute_real_medido", "azimute") or 0.0)

        # Convenção de mina:
        # -90 = vertical para baixo
        #   0 = horizontal
        # +90 = vertical para cima
        zen0 = math.radians(90 + inc0)
        az0r = math.radians(az0)

        dx = md0 * math.sin(zen0) * math.sin(az0r)
        dy = md0 * math.sin(zen0) * math.cos(az0r)
        dz = md0 * math.cos(zen0)

        x += dx
        y += dy
        z += dz

    pontos.append((x, y, z))
    doglegs.append(0.0)
    alertas.append("OK")

    if len(medicoes) == 1:
        return pontos, doglegs, alertas

    # -------------------------------------------------
    # 2) TROÇOS ENTRE MEDIÇÕES CONSECUTIVAS
    # -------------------------------------------------
    for i in range(1, len(medicoes)):
        p1, p2 = medicoes[i - 1], medicoes[i]

        md1 = float(_valor_medicao(p1, "profundidade_medida", "profundidade") or 0.0)
        md2 = float(_valor_medicao(p2, "profundidade_medida", "profundidade") or 0.0)
        dmd = md2 - md1

        if dmd <= 0:
            pontos.append((x, y, z))
            doglegs.append(0.0)
            alertas.append("OK")
            continue

        inc1 = float(_valor_medicao(p1, "inclinacao_real_medida", "inclinacao") or 0.0)
        inc2 = float(_valor_medicao(p2, "inclinacao_real_medida", "inclinacao") or 0.0)

        zen1 = math.radians(90 + inc1)
        zen2 = math.radians(90 + inc2)

        a1 = math.radians(float(_valor_medicao(p1, "azimute_real_medido", "azimute") or 0.0))
        a2 = math.radians(float(_valor_medicao(p2, "azimute_real_medido", "azimute") or 0.0))

        cos_beta = (
            math.cos(zen1) * math.cos(zen2)
            + math.sin(zen1) * math.sin(zen2) * math.cos(a2 - a1)
        )
        cos_beta = max(min(cos_beta, 1.0), -1.0)

        dogleg = math.acos(cos_beta)
        rf = (2 / dogleg) * math.tan(dogleg / 2) if dogleg > 1e-7 else 1.0

        dx = (dmd / 2.0) * (
            math.sin(zen1) * math.sin(a1) +
            math.sin(zen2) * math.sin(a2)
        ) * rf

        dy = (dmd / 2.0) * (
            math.sin(zen1) * math.cos(a1) +
            math.sin(zen2) * math.cos(a2)
        ) * rf

        dz = (dmd / 2.0) * (
            math.cos(zen1) + math.cos(zen2)
        ) * rf

        x += dx
        y += dy
        z += dz

        pontos.append((x, y, z))

        dogleg_deg = math.degrees(dogleg)
        dls = (dogleg_deg / dmd) * 30 if dmd != 0 else 0.0
        doglegs.append(dls)

        if dls > 5:
            alertas.append("CRÍTICO")
        elif dls > 3:
            alertas.append("ATENÇÃO")
        else:
            alertas.append("OK")

    return pontos, doglegs, alertas

def calcular_linha_planeada(origem, inclinacao, azimute, comprimento):
    """
    Gera uma linha teórica planeada para o furo.

    Convenção:
    - inclinação negativa -> furo desce
    - inclinação positiva -> furo sobe
    - z representa profundidade vertical (TVD) para baixo no gráfico
    """
    x0, y0, z0 = origem

    comprimento = float(comprimento or 0.0)
    inclinacao = float(inclinacao or 0.0)
    azimute = float(azimute or 0.0)

    inc_rad = math.radians(inclinacao)
    azi_rad = math.radians(azimute)

    desloc_horizontal = comprimento * math.cos(inc_rad)
    dx = desloc_horizontal * math.sin(azi_rad)
    dy = desloc_horizontal * math.cos(azi_rad)

    # inclinação negativa => desce
    delta_z = -comprimento * math.sin(inc_rad)

    return {
        "x": [x0, x0 + dx],
        "y": [y0, y0 + dy],
        "z": [z0, z0 + delta_z],
    }
    desloc_horizontal = comprimento * math.sin(inc_rad)
    dx = desloc_horizontal * math.sin(azi_rad)
    dy = desloc_horizontal * math.cos(azi_rad)
    dz = comprimento * math.cos(inc_rad)

    return {
        "x": [x0, x0 + dx],
        "y": [y0, y0 + dy],
        "z": [z0, z0 - dz],
    }


def interpolar_ponto_por_md(pontos, mds, target_md):
    if not pontos or not mds:
        return None

    if target_md <= mds[0]:
        return pontos[0]
    if target_md >= mds[-1]:
        return pontos[-1]

    for idx in range(1, len(mds)):
        md1 = float(mds[idx - 1] or 0.0)
        md2 = float(mds[idx] or 0.0)
        if md2 <= md1:
            continue
        if target_md <= md2:
            ratio = (target_md - md1) / (md2 - md1)
            x1, y1, z1 = pontos[idx - 1]
            x2, y2, z2 = pontos[idx]
            return (
                x1 + ((x2 - x1) * ratio),
                y1 + ((y2 - y1) * ratio),
                z1 + ((z2 - z1) * ratio),
            )

    return pontos[-1]


def construir_segmentos_tubos(pontos, mds, comprimento_frontal, comprimento_padrao, total_md=None):
    if not pontos or not mds:
        return {"segmentos": [], "juntas": []}

    comprimento_frontal = float(comprimento_frontal or 0.0)
    comprimento_padrao = float(comprimento_padrao or 0.0)
    total_md = float(total_md if total_md is not None else (mds[-1] or 0.0))

    if total_md <= 0:
        return {"segmentos": [], "juntas": []}

    if comprimento_padrao <= 0:
        comprimento_padrao = 3.0

    limites = [0.0]
    if comprimento_frontal > 0:
        limites.append(min(comprimento_frontal, total_md))

    cursor = limites[-1]
    while cursor < total_md:
        cursor = min(cursor + comprimento_padrao, total_md)
        if cursor > limites[-1]:
            limites.append(cursor)

    segmentos = []
    juntas = []
    tubo_regular_numero = 0

    for idx in range(1, len(limites)):
        md_inicio = limites[idx - 1]
        md_fim = limites[idx]
        ponto_inicio = interpolar_ponto_por_md(pontos, mds, md_inicio)
        ponto_fim = interpolar_ponto_por_md(pontos, mds, md_fim)
        if not ponto_inicio or not ponto_fim:
            continue

        segmento_frontal = idx == 1 and comprimento_frontal > 0
        if segmento_frontal:
            tubo_numero = None
            rotulo = "Conjunto de fundo"
        else:
            tubo_regular_numero += 1
            tubo_numero = tubo_regular_numero
            rotulo = f"Tubo número {tubo_numero}"

        segmentos.append(
            {
                "inicio_md": md_inicio,
                "fim_md": md_fim,
                "inicio": ponto_inicio,
                "fim": ponto_fim,
                "tipo": "frontal" if segmento_frontal else "regular",
                "indice": idx - 1,
                "tubo_numero": tubo_numero,
                "rotulo": rotulo,
            }
        )

        if idx < len(limites) - 1:
            proximo_segmento_frontal = idx + 1 == 1 and comprimento_frontal > 0
            if proximo_segmento_frontal:
                proximo_rotulo = "Conjunto de fundo"
                proximo_tubo_numero = None
            else:
                proximo_tubo_numero = tubo_regular_numero + 1
                proximo_rotulo = f"Tubo número {proximo_tubo_numero}"

            juntas.append(
                {
                    "md": md_fim,
                    "ponto": ponto_fim,
                    "indice": idx - 1,
                    "rotulo_atual": rotulo,
                    "tubo_numero_atual": tubo_numero,
                    "rotulo_proximo": proximo_rotulo,
                    "tubo_numero_proximo": proximo_tubo_numero,
                }
            )

    return {"segmentos": segmentos, "juntas": juntas}
    x0, y0, z0 = origem

    comprimento = float(comprimento or 0.0)
    inclinacao = float(inclinacao or 0.0)
    azimute = float(azimute or 0.0)

    inc_rad = math.radians(abs(inclinacao))
    azi_rad = math.radians(azimute)

    desloc_horizontal = comprimento * math.sin(inc_rad)
    dx = desloc_horizontal * math.sin(azi_rad)
    dy = desloc_horizontal * math.cos(azi_rad)
    dz = comprimento * math.cos(inc_rad)

    return {
        "x": [x0, x0 + dx],
        "y": [y0, y0 + dy],
        "z": [z0, z0 - dz],
    }
    x0, y0, z0 = origem

    inc_rad = math.radians(abs(inclinacao or 0))
    azi_rad = math.radians(azimute or 0)

    desloc_horizontal = comprimento * math.sin(inc_rad)
    dx = desloc_horizontal * math.sin(azi_rad)
    dy = desloc_horizontal * math.cos(azi_rad)
    dz = comprimento * math.cos(inc_rad)

    return {
        "x": [x0, x0 + dx],
        "y": [y0, y0 + dy],
        "z": [z0, z0 - dz],
    }
