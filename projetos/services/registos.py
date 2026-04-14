from datetime import timedelta

from django.db import transaction

from projetos.models import Furo, RegistoDiarioEmpregado
from projetos.services.empregados import recalcular_resumo_empregado
from projetos.services.furos import recalcular_resumo_furo


def _preencher_snapshot_furo_no_registo(registo, furo):
    profundidade_antes = furo.profundidade_atual or 0.0
    metros_novos = registo.metros_furados or 0.0
    profundidade_depois = profundidade_antes + metros_novos

    registo.profundidade_furo_antes = profundidade_antes
    registo.profundidade_furo_depois = profundidade_depois

    # Snapshot do planeamento inicial
    registo.profundidade_alvo_inicial_furo = furo.profundidade_alvo_inicial or 0.0
    registo.inclinacao_planeada_inicial_furo = furo.inclinacao_planeada_inicial
    registo.azimute_planeado_inicial_furo = furo.azimute_planeado_inicial

    # Snapshot do planeamento atual
    registo.profundidade_alvo_atual_furo = furo.profundidade_alvo_atual or 0.0
    registo.inclinacao_planeada_atual_furo = furo.inclinacao_planeada_atual
    registo.azimute_planeado_atual_furo = furo.azimute_planeado_atual

    # Snapshot do estado real atual
    registo.inclinacao_real_atual_furo = furo.inclinacao_real_atual
    registo.azimute_real_atual_furo = furo.azimute_real_atual


@transaction.atomic
def criar_registo_diario(form, empregado):
    registo = form.save(commit=False)
    registo.empregado = empregado

    furo = None
    if registo.furo_id:
        furo = Furo.objects.select_for_update().get(pk=registo.furo_id)
        _preencher_snapshot_furo_no_registo(registo, furo)

    registo.save()

    if furo:
        furo.profundidade_atual = registo.profundidade_furo_depois

        profundidade_maxima_atual = furo.profundidade_maxima_atingida or 0.0
        if profundidade_maxima_atual < registo.profundidade_furo_depois:
            furo.profundidade_maxima_atingida = registo.profundidade_furo_depois

        total_horas_atual = furo.total_horas or timedelta()
        horas_registo = registo.horas_trabalhadas_furo or timedelta()
        furo.total_horas = total_horas_atual + horas_registo

        furo.save(update_fields=[
            "profundidade_atual",
            "profundidade_maxima_atingida",
            "total_horas",
        ])

    recalcular_resumo_empregado(empregado)

    if registo.furo:
        recalcular_resumo_furo(registo.furo)

    return registo


@transaction.atomic
def atualizar_registo_diario(registo, form):
    empregado = registo.empregado
    furo_antigo = registo.furo

    registo_atualizado = form.save(commit=False)
    registo_atualizado.pk = registo.pk

    furo_novo = None
    if registo_atualizado.furo_id:
        furo_novo = Furo.objects.select_for_update().get(pk=registo_atualizado.furo_id)
        _preencher_snapshot_furo_no_registo(registo_atualizado, furo_novo)

    registo_atualizado.save()

    recalcular_resumo_empregado(empregado)

    if furo_antigo:
        recalcular_resumo_furo(furo_antigo)

    if registo_atualizado.furo and registo_atualizado.furo != furo_antigo:
        recalcular_resumo_furo(registo_atualizado.furo)
    elif registo_atualizado.furo:
        recalcular_resumo_furo(registo_atualizado.furo)

    return registo_atualizado