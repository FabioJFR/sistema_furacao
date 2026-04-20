from projetos.models import Empregados, Furo



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _filtrar_por_empresa(queryset, empresa=None, campo="empresa_id"):
    if empresa is None:
        return queryset

    empresa_id = _resolver_empresa_id(empresa)
    return queryset.filter(**{campo: empresa_id})



def _obter_queryset_base_empregados():
    return Empregados.objects.all()



def _obter_dados_grafico_registos(registos_grafico):
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
        "grafico_labels": labels,
        "grafico_metros": metros_por_dia,
        "grafico_horas": horas_por_dia,
        "grafico_produtividade": produtividade_por_dia,
    }



def _contexto_empregado_vazio(empregado):
    return {
        "empregado": empregado,
        "horas_hoje": 0,
        "horas_mes": 0,
        "horas_total": 0,
        "metros_hoje": 0,
        "metros_total": 0,
        "total_furos": 0,
        "media_metros_hora": 0,
        "media_metros_dia": 0,
        "ultimos_registos": empregado.registos_diarios.none(),
        "grafico_labels": [],
        "grafico_metros": [],
        "grafico_horas": [],
        "grafico_produtividade": [],
        "furos_trabalhados": Furo.objects.none(),
    }



def obter_lista_empregados(empresa=None):
    queryset = _obter_queryset_base_empregados().order_by("nome")
    return _filtrar_por_empresa(queryset, empresa)



def obter_empregados_pendentes(empresa=None):
    queryset = _obter_queryset_base_empregados().filter(aprovado=False).order_by("-data_registo")
    return _filtrar_por_empresa(queryset, empresa)



def obter_contexto_area_empregado(empregado, empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    if empresa_id is not None and empregado.empresa_id != empresa_id:
        return _contexto_empregado_vazio(empregado)

    furos_trabalhados = Furo.objects.filter(registos_furo__empregado=empregado).distinct()
    ultimos_registos = empregado.registos_diarios.select_related("projeto", "furo")[:5]
    registos_grafico = empregado.registos_diarios.order_by("data", "criado_em")

    if empresa_id is not None:
        furos_trabalhados = furos_trabalhados.filter(empresa_id=empresa_id)
        ultimos_registos = ultimos_registos.filter(empresa_id=empresa_id)
        registos_grafico = registos_grafico.filter(empresa_id=empresa_id)

    dados_grafico = _obter_dados_grafico_registos(registos_grafico)

    return {
        "empregado": empregado,
        "horas_hoje": empregado.horas_diarias or 0,
        "horas_mes": empregado.horas_trabalhadas_mes or 0,
        "horas_total": empregado.horas_total or 0,
        "metros_hoje": empregado.metros_furados_hoje or 0,
        "metros_total": empregado.total_metros_furados or 0,
        "total_furos": empregado.total_furos_trabalhados or 0,
        "media_metros_hora": empregado.media_metros_por_hora or 0,
        "media_metros_dia": empregado.media_metros_por_dia or 0,
        "ultimos_registos": ultimos_registos,
        "furos_trabalhados": furos_trabalhados,
        **dados_grafico,
    }