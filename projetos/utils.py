import math

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
    md0 = float(p0.profundidade or 0.0)

    if md0 > 0:
        inc0 = float(p0.inclinacao or 0.0)
        az0 = float(p0.azimute or 0.0)

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

        md1 = float(p1.profundidade or 0.0)
        md2 = float(p2.profundidade or 0.0)
        dmd = md2 - md1

        if dmd <= 0:
            pontos.append((x, y, z))
            doglegs.append(0.0)
            alertas.append("OK")
            continue

        inc1 = float(p1.inclinacao or 0.0)
        inc2 = float(p2.inclinacao or 0.0)

        zen1 = math.radians(90 + inc1)
        zen2 = math.radians(90 + inc2)

        a1 = math.radians(float(p1.azimute or 0.0))
        a2 = math.radians(float(p2.azimute or 0.0))

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