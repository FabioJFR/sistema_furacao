def eh_marcador_azul(r, g, b):
    return b >= 70 and b > r * 1.18 and b > g * 1.08 and (b - r) >= 24


def eh_marcador_preto(r, g, b):
    return max(r, g, b) <= 95 and (max(r, g, b) - min(r, g, b)) <= 28
