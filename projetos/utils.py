# projetos/utils.py
import math

def calcular_trajetoria_min_curv(medicoes):
    pontos = [(0, 0, 0)]

    x, y, z = 0, 0, 0

    for i in range(1, len(medicoes)):
        m1 = medicoes[i - 1]
        m2 = medicoes[i]

        inc1 = math.radians(m1.inclinacao)
        azi1 = math.radians(m1.azimute)

        inc2 = math.radians(m2.inclinacao)
        azi2 = math.radians(m2.azimute)

        md = m2.profundidade - m1.profundidade

        cos_beta = (
            math.cos(inc1) * math.cos(inc2) +
            math.sin(inc1) * math.sin(inc2) * math.cos(azi2 - azi1)
        )

        beta = math.acos(max(min(cos_beta, 1), -1))

        if beta != 0:
            rf = (2 / beta) * math.tan(beta / 2)
        else:
            rf = 1

        dx = (md / 2) * (
            math.sin(inc1) * math.cos(azi1) +
            math.sin(inc2) * math.cos(azi2)
        ) * rf

        dy = (md / 2) * (
            math.sin(inc1) * math.sin(azi1) +
            math.sin(inc2) * math.sin(azi2)
        ) * rf

        dz = (md / 2) * (
            math.cos(inc1) + math.cos(inc2)
        ) * rf

        x += dx
        y += dy
        z -= dz

        pontos.append((x, y, z))

    return pontos