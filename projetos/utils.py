import math
from django.utils import timezone
from django.db.models import Sum

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


def recalcular_resumo_empregado(empregado):
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)

    registos = empregado.registos_diarios.all()

    total_horas = registos.aggregate(total=Sum('horas_trabalhadas'))['total'] or 0
    total_metros = registos.aggregate(total=Sum('metros_furados'))['total'] or 0

    horas_mes = registos.filter(
        data__gte=inicio_mes,
        data__lte=hoje
    ).aggregate(total=Sum('horas_trabalhadas'))['total'] or 0

    metros_mes = registos.filter(
        data__gte=inicio_mes,
        data__lte=hoje
    ).aggregate(total=Sum('metros_furados'))['total'] or 0

    horas_hoje = registos.filter(
        data=hoje
    ).aggregate(total=Sum('horas_trabalhadas'))['total'] or 0

    metros_hoje = registos.filter(
        data=hoje
    ).aggregate(total=Sum('metros_furados'))['total'] or 0

    total_furos = registos.exclude(
        furo__isnull=True
    ).values('furo').distinct().count()

    total_dias = registos.values('data').distinct().count()

    media_m_h = total_metros / total_horas if total_horas > 0 else 0
    media_m_d = total_metros / total_dias if total_dias > 0 else 0

    empregado.total_metros_furados = total_metros
    empregado.metros_furados_mes = metros_mes
    empregado.metros_furados_hoje = metros_hoje
    empregado.total_furos_trabalhados = total_furos
    empregado.media_metros_por_hora = round(media_m_h, 2)
    empregado.media_metros_por_dia = round(media_m_d, 2)

    empregado.horas_total = total_horas
    empregado.horas_trabalhadas_mes = horas_mes
    empregado.horas_diarias = horas_hoje

    empregado.save(update_fields=[
        'total_metros_furados',
        'metros_furados_mes',
        'metros_furados_hoje',
        'total_furos_trabalhados',
        'media_metros_por_hora',
        'media_metros_por_dia',
        'horas_total',
        'horas_trabalhadas_mes',
        'horas_diarias',
    ])

