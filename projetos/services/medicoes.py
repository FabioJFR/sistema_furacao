from projetos.models import Medicao


def atualizar_resumo_furo(furo, medicao_referencia=None):
    medicoes = furo.medicoes.all()

    profundidades = [
        m.profundidade_medida or 0.0
        for m in medicoes
        if m.profundidade_medida is not None
    ]

    profundidade_max_medida = max(profundidades, default=furo.profundidade_inicial or 0.0)

    # A profundidade atual do furo só sobe se a medição for mais funda
    if (furo.profundidade_atual or 0.0) < profundidade_max_medida:
        furo.profundidade_atual = profundidade_max_medida

    # Guardar também a maior profundidade atingida
    furo.profundidade_maxima_atingida = max(
        furo.profundidade_maxima_atingida or 0.0,
        profundidade_max_medida,
    )

    # Atualizar apenas o estado real atual do furo
    if medicao_referencia is not None:
        if medicao_referencia.inclinacao_real_medida is not None:
            furo.inclinacao_real_atual = medicao_referencia.inclinacao_real_medida

        if medicao_referencia.azimute_real_medido is not None:
            furo.azimute_real_atual = medicao_referencia.azimute_real_medido

        if medicao_referencia.magnetismo is not None:
            furo.magnetismo = medicao_referencia.magnetismo

    furo.save(update_fields=[
        "profundidade_atual",
        "profundidade_maxima_atingida",
        "inclinacao_real_atual",
        "azimute_real_atual",
        "magnetismo",
    ])
    return furo


def criar_medicao(form, furo=None):
    medicao = form.save(commit=False)

    if furo is not None:
        medicao.furo = furo
        medicao.nome_furo_snapshot = furo.nome

        # Herdar localização do furo se a medição não trouxer
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

    if medicao.furo:
        atualizar_resumo_furo(medicao.furo, medicao)

    return medicao


def atualizar_medicao(form):
    medicao = form.save(commit=False)

    # Reforçar snapshot do planeamento atual no momento da edição
    if medicao.furo:
        medicao.nome_furo_snapshot = medicao.furo.nome

        medicao.profundidade_alvo_inicial_furo = medicao.furo.profundidade_alvo_inicial
        medicao.profundidade_alvo_atual_furo = medicao.furo.profundidade_alvo_atual

        medicao.inclinacao_planeada_inicial_furo = medicao.furo.inclinacao_planeada_inicial
        medicao.inclinacao_planeada_atual_furo = medicao.furo.inclinacao_planeada_atual

        medicao.azimute_planeado_inicial_furo = medicao.furo.azimute_planeado_inicial
        medicao.azimute_planeado_atual_furo = medicao.furo.azimute_planeado_atual

    medicao.save()

    if medicao.furo:
        atualizar_resumo_furo(medicao.furo, medicao)

    return medicao