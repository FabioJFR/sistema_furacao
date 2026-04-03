import math

def calcular_trajetoria_min_curv(medicoes, profundidade_inicial=0.0):
    x, y, z = 0.0, 0.0, profundidade_inicial
    pontos = [(x, y, z)]
    doglegs = [0.0]
    alertas = ["OK"]

    if not medicoes or len(medicoes) == 1:
        return pontos, doglegs, alertas

    for i in range(1, len(medicoes)):
        p1, p2 = medicoes[i - 1], medicoes[i]

        md1 = p1.profundidade or 0.0
        md2 = p2.profundidade or 0.0
        dmd = md2 - md1

        if dmd <= 0:
            # evita cálculo inválido e mantém coerência
            pontos.append((x, y, z))
            doglegs.append(0.0)
            alertas.append("OK")
            continue

        I1 = math.radians(p1.inclinacao or 0.0)
        I2 = math.radians(p2.inclinacao or 0.0)
        A1 = math.radians(p1.azimute or 0.0)
        A2 = math.radians(p2.azimute or 0.0)

        cos_beta = (
            math.cos(I1) * math.cos(I2)
            + math.sin(I1) * math.sin(I2) * math.cos(A2 - A1)
        )
        cos_beta = max(min(cos_beta, 1.0), -1.0)

        dogleg = math.acos(cos_beta)

        rf = (2 / dogleg) * math.tan(dogleg / 2) if dogleg > 1e-7 else 1.0

        dx = (dmd / 2) * (
            math.sin(I1) * math.sin(A1) + math.sin(I2) * math.sin(A2)
        ) * rf

        dy = (dmd / 2) * (
            math.sin(I1) * math.cos(A1) + math.sin(I2) * math.cos(A2)
        ) * rf

        dz = (dmd / 2) * (
            math.cos(I1) + math.cos(I2)
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