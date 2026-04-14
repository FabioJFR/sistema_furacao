from projetos.models import Empregados, Furo


def obter_lista_empregados():
    return Empregados.objects.all().order_by("nome")


def obter_empregados_pendentes():
    return Empregados.objects.filter(aprovado=False).order_by("-data_registo")


def obter_contexto_area_empregado(empregado):
    furos_trabalhados = Furo.objects.filter(
        registos_furo__empregado=empregado
    ).distinct()

    ultimos_registos = empregado.registos_diarios.select_related(
        "projeto", "furo"
    ).all()[:5]

    horas_hoje = empregado.horas_diarias or 0
    horas_mes = empregado.horas_trabalhadas_mes or 0
    horas_total = empregado.horas_total or 0

    metros_hoje = empregado.metros_furados_hoje or 0
    metros_total = empregado.total_metros_furados or 0

    total_furos = empregado.total_furos_trabalhados or 0
    media_metros_hora = empregado.media_metros_por_hora or 0
    media_metros_dia = empregado.media_metros_por_dia or 0

    registos_grafico = empregado.registos_diarios.order_by("data")

    labels = []
    metros_por_dia = []
    horas_por_dia = []
    produtividade_por_dia = []

    agregados = {}

    for registo in registos_grafico:
        if not registo.data:
            continue

        chave = registo.data.strftime("%d/%m/%Y")

        if chave not in agregados:
            agregados[chave] = {
                "metros": 0,
                "horas": 0,
            }

        agregados[chave]["metros"] += registo.metros_furados or 0
        agregados[chave]["horas"] += registo.horas_trabalhadas or 0

    for data_label, valores in agregados.items():
        labels.append(data_label)
        metros = valores["metros"]
        horas = valores["horas"]
        produtividade = (metros / horas) if horas > 0 else 0

        metros_por_dia.append(round(metros, 2))
        horas_por_dia.append(round(horas, 2))
        produtividade_por_dia.append(round(produtividade, 2))

    return {
        "empregado": empregado,
        "horas_hoje": horas_hoje,
        "horas_mes": horas_mes,
        "horas_total": horas_total,
        "metros_hoje": metros_hoje,
        "metros_total": metros_total,
        "total_furos": total_furos,
        "media_metros_hora": media_metros_hora,
        "media_metros_dia": media_metros_dia,
        "ultimos_registos": ultimos_registos,
        "grafico_labels": labels,
        "grafico_metros": metros_por_dia,
        "grafico_horas": horas_por_dia,
        "grafico_produtividade": produtividade_por_dia,
        "furos_trabalhados": furos_trabalhados,
    }