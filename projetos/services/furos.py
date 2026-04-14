from datetime import timedelta

from projetos.models import Furo, RegistoDiarioEmpregado


def preparar_furo_novo(furo):
    # Coordenadas base
    furo.origem_este = furo.origem_este or 0.0
    furo.origem_norte = furo.origem_norte or 0.0
    furo.origem_tvd = furo.origem_tvd or 0.0

    # Profundidade atual arranca na profundidade inicial
    furo.profundidade_atual = furo.profundidade_inicial or 0.0

    # Profundidade máxima atingida arranca na profundidade atual
    if (furo.profundidade_maxima_atingida or 0.0) < (furo.profundidade_atual or 0.0):
        furo.profundidade_maxima_atingida = furo.profundidade_atual

    # Planeamento atual arranca igual ao planeamento inicial
    if furo.profundidade_alvo_atual is None:
        furo.profundidade_alvo_atual = furo.profundidade_alvo_inicial

    if furo.inclinacao_planeada_atual is None:
        furo.inclinacao_planeada_atual = furo.inclinacao_planeada_inicial

    if furo.azimute_planeado_atual is None:
        furo.azimute_planeado_atual = furo.azimute_planeado_inicial

    # Estado real inicial pode arrancar com o planeado inicial
    if furo.inclinacao_real_atual is None:
        furo.inclinacao_real_atual = furo.inclinacao_planeada_inicial

    if furo.azimute_real_atual is None:
        furo.azimute_real_atual = furo.azimute_planeado_inicial

    return furo


def criar_furo(form):
    furo = form.save(commit=False)
    preparar_furo_novo(furo)
    furo.save()
    form.save_m2m()
    return furo


def atualizar_furo(form):
    furo = form.save(commit=False)

    # Coordenadas base
    furo.origem_este = furo.origem_este or 0.0
    furo.origem_norte = furo.origem_norte or 0.0
    furo.origem_tvd = furo.origem_tvd or 0.0

    # Garantir coerência entre profundidade atual e máxima atingida
    profundidade_atual = furo.profundidade_atual or 0.0
    profundidade_maxima = furo.profundidade_maxima_atingida or 0.0

    if profundidade_maxima < profundidade_atual:
        furo.profundidade_maxima_atingida = profundidade_atual

    # Se não existirem medições nem registos, manter o furo num estado inicial coerente
    if not furo.medicoes.exists() and not furo.registos_furo.exists():
        furo.profundidade_atual = furo.profundidade_inicial or 0.0
        furo.profundidade_maxima_atingida = furo.profundidade_atual

    # Garantir que os campos "atuais" do planeamento não ficam vazios
    if furo.profundidade_alvo_atual is None:
        furo.profundidade_alvo_atual = furo.profundidade_alvo_inicial

    if furo.inclinacao_planeada_atual is None:
        furo.inclinacao_planeada_atual = furo.inclinacao_planeada_inicial

    if furo.azimute_planeado_atual is None:
        furo.azimute_planeado_atual = furo.azimute_planeado_inicial

    furo.save()
    form.save_m2m()
    return furo


def atualizar_resumo_furo_com_medicao(furo, medicao):
    return recalcular_resumo_furo(furo)


def criar_medicao_para_furo(form, furo):
    medicao = form.save(commit=False)
    medicao.furo = furo
    medicao.nome_furo_snapshot = furo.nome

    # Herdar localização do furo se não for dada na medição
    if medicao.latitude is None:
        medicao.latitude = furo.latitude
    if medicao.longitude is None:
        medicao.longitude = furo.longitude
    if medicao.altitude is None:
        medicao.altitude = furo.altitude

    # Snapshot do planeamento do furo no momento da medição
    medicao.profundidade_alvo_inicial_furo = furo.profundidade_alvo_inicial
    medicao.profundidade_alvo_atual_furo = furo.profundidade_alvo_atual

    medicao.inclinacao_planeada_inicial_furo = furo.inclinacao_planeada_inicial
    medicao.inclinacao_planeada_atual_furo = furo.inclinacao_planeada_atual

    medicao.azimute_planeado_inicial_furo = furo.azimute_planeado_inicial
    medicao.azimute_planeado_atual_furo = furo.azimute_planeado_atual

    medicao.save()

    # Atualizar estado real atual do furo com base na nova medição
    if medicao.inclinacao_real_medida is not None:
        furo.inclinacao_real_atual = medicao.inclinacao_real_medida

    if medicao.azimute_real_medido is not None:
        furo.azimute_real_atual = medicao.azimute_real_medido

    if medicao.profundidade_medida is not None:
        if (furo.profundidade_atual or 0.0) < medicao.profundidade_medida:
            furo.profundidade_atual = medicao.profundidade_medida

        if (furo.profundidade_maxima_atingida or 0.0) < medicao.profundidade_medida:
            furo.profundidade_maxima_atingida = medicao.profundidade_medida

    furo.save(update_fields=[
        "inclinacao_real_atual",
        "azimute_real_atual",
        "profundidade_atual",
        "profundidade_maxima_atingida",
    ])

    atualizar_resumo_furo_com_medicao(furo, medicao)

    return medicao


def recalcular_resumo_furo(furo):
    registos = (
        RegistoDiarioEmpregado.objects
        .filter(furo=furo)
        .order_by("data", "criado_em")
    )

    profundidade_corrente = furo.profundidade_inicial or 0.0
    profundidade_maxima = profundidade_corrente
    total_horas = timedelta()

    registos_para_atualizar = []

    for registo in registos:
        metros_turno = registo.metros_furados or 0.0

        profundidade_antes = profundidade_corrente
        profundidade_depois = profundidade_antes + metros_turno

        alterou = False

        if registo.profundidade_furo_antes != profundidade_antes:
            registo.profundidade_furo_antes = profundidade_antes
            alterou = True

        if registo.profundidade_furo_depois != profundidade_depois:
            registo.profundidade_furo_depois = profundidade_depois
            alterou = True

        if alterou:
            registos_para_atualizar.append(registo)

        profundidade_corrente = profundidade_depois

        if profundidade_corrente > profundidade_maxima:
            profundidade_maxima = profundidade_corrente

        total_horas += registo.horas_trabalhadas_furo or timedelta()

    if registos_para_atualizar:
        RegistoDiarioEmpregado.objects.bulk_update(
            registos_para_atualizar,
            ["profundidade_furo_antes", "profundidade_furo_depois"]
        )

    furo.profundidade_atual = profundidade_corrente
    furo.profundidade_maxima_atingida = profundidade_maxima
    furo.total_horas = total_horas

    furo.save(update_fields=[
        "profundidade_atual",
        "profundidade_maxima_atingida",
        "total_horas",
    ])

    return furo