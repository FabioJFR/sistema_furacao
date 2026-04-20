from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from projetos.models import Furo
from projetos.services.empregados import recalcular_resumo_empregado
from projetos.services.furos import recalcular_resumo_furo



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _obter_furo_para_registo(furo_id, empregado):
    queryset = Furo.objects.select_for_update()

    if empregado.empresa_id:
        queryset = queryset.filter(empresa_id=empregado.empresa_id)

    return queryset.get(pk=furo_id)



def _validar_registo_multiempresa(registo, empregado, furo=None):
    if empregado.empresa_id:
        if registo.empresa_id and registo.empresa_id != empregado.empresa_id:
            raise ValidationError("O registo não pertence à empresa do empregado.")

        if registo.projeto_id and registo.projeto and registo.projeto.empresa_id != empregado.empresa_id:
            raise ValidationError("O projeto do registo não pertence à empresa do empregado.")

        if furo and furo.empresa_id != empregado.empresa_id:
            raise ValidationError("O furo do registo não pertence à empresa do empregado.")

    if registo.projeto_id and furo and furo.projeto_id != registo.projeto_id:
        raise ValidationError("O furo selecionado não pertence ao projeto do registo.")



def _preencher_snapshot_furo_no_registo(registo, furo):
    profundidade_antes = furo.profundidade_atual or 0.0
    metros_novos = registo.metros_furados or 0.0
    profundidade_depois = profundidade_antes + metros_novos

    registo.profundidade_furo_antes = profundidade_antes
    registo.profundidade_furo_depois = profundidade_depois

    registo.profundidade_alvo_inicial_furo = furo.profundidade_alvo_inicial or 0.0
    registo.inclinacao_planeada_inicial_furo = furo.inclinacao_planeada_inicial
    registo.azimute_planeado_inicial_furo = furo.azimute_planeado_inicial

    registo.profundidade_alvo_atual_furo = furo.profundidade_alvo_atual or 0.0
    registo.inclinacao_planeada_atual_furo = furo.inclinacao_planeada_atual
    registo.azimute_planeado_atual_furo = furo.azimute_planeado_atual

    registo.inclinacao_real_atual_furo = furo.inclinacao_real_atual
    registo.azimute_real_atual_furo = furo.azimute_real_atual



def _preparar_registo_para_guardar(registo, empregado):
    registo.empregado = empregado
    registo.empresa = empregado.empresa

    if not registo.furo_id:
        _validar_registo_multiempresa(registo, empregado)
        return None

    furo = _obter_furo_para_registo(registo.furo_id, empregado)
    _validar_registo_multiempresa(registo, empregado, furo=furo)
    _preencher_snapshot_furo_no_registo(registo, furo)
    return furo



def _atualizar_resumo_furo_com_registo(furo, registo):
    furo.profundidade_atual = registo.profundidade_furo_depois

    profundidade_maxima_atual = furo.profundidade_maxima_atingida or 0.0
    if profundidade_maxima_atual < registo.profundidade_furo_depois:
        furo.profundidade_maxima_atingida = registo.profundidade_furo_depois

    total_horas_atual = furo.total_horas or timedelta()
    horas_registo = registo.horas_trabalhadas_furo or timedelta()
    furo.total_horas = total_horas_atual + horas_registo

    furo.save(
        update_fields=[
            "profundidade_atual",
            "profundidade_maxima_atingida",
            "total_horas",
        ]
    )



def _recalcular_dependencias_registo(empregado, furo_antigo=None, furo_novo=None):
    recalcular_resumo_empregado(empregado)

    if furo_antigo:
        recalcular_resumo_furo(furo_antigo)

    if furo_novo and (not furo_antigo or furo_novo.pk != furo_antigo.pk):
        recalcular_resumo_furo(furo_novo)



@transaction.atomic
def criar_registo_diario(form, empregado):
    registo = form.save(commit=False)
    furo = _preparar_registo_para_guardar(registo, empregado)

    registo.save()

    if furo:
        _atualizar_resumo_furo_com_registo(furo, registo)

    _recalcular_dependencias_registo(empregado, furo_novo=registo.furo)
    return registo



@transaction.atomic
def atualizar_registo_diario(registo, form):
    empregado = registo.empregado
    furo_antigo = registo.furo

    registo_atualizado = form.save(commit=False)
    registo_atualizado.pk = registo.pk
    furo_novo = _preparar_registo_para_guardar(registo_atualizado, empregado)

    registo_atualizado.save()

    _recalcular_dependencias_registo(
        empregado,
        furo_antigo=furo_antigo,
        furo_novo=registo_atualizado.furo,
    )

    return registo_atualizado