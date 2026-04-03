# projetos/utils.py
import math

def calcular_trajetoria_min_curv(medicoes):
    x, y, z = 0, 0, 0
    pontos = [(x, y, z)]
    doglegs = [0]
    alertas = ["OK"]  # primeiro ponto

    for i in range(1, len(medicoes)):
        p1, p2 = medicoes[i-1], medicoes[i]
        dmd = p2.profundidade - p1.profundidade

        I1 = math.radians(p1.inclinacao or 0)
        I2 = math.radians(p2.inclinacao or 0)
        A1 = math.radians(p1.azimute or 0)
        A2 = math.radians(p2.azimute or 0)

        # Dogleg robusto
        cos_beta = (math.cos(I1) * math.cos(I2)) + \
                   (math.sin(I1) * math.sin(I2) * math.cos(A2 - A1))
        cos_beta = max(min(cos_beta, 1.0), -1.0)

        dogleg = math.acos(cos_beta)

        # Ratio Factor
        RF = (2 / dogleg) * math.tan(dogleg / 2) if dogleg > 1e-7 else 1

        # Incrementos (East, North, TVD)
        dx = (dmd / 2) * (math.sin(I1) * math.sin(A1) + math.sin(I2) * math.sin(A2)) * RF
        dy = (dmd / 2) * (math.sin(I1) * math.cos(A1) + math.sin(I2) * math.cos(A2)) * RF
        dz = (dmd / 2) * (math.cos(I1) + math.cos(I2)) * RF

        x += dx
        y += dy
        z += dz

        pontos.append((x, y, z))

        # Dogleg Severity (°/30m)
        dogleg_deg = math.degrees(dogleg)
        dls = (dogleg_deg / dmd) * 30 if dmd != 0 else 0
        doglegs.append(dls)

        # 🚨 ALERTAS
        if dls > 5:
            alertas.append("CRÍTICO")
        elif dls > 3:
            alertas.append("ATENÇÃO")
        else:
            alertas.append("OK")

    return pontos, doglegs, alertas
