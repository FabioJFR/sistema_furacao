from django.utils import timezone

from projetos.models import MaquinaEventoOperacional


def criar_evento_operacional_maquina(
    *,
    maquina,
    tipo_evento,
    projeto=None,
    furo=None,
    empregado=None,
    registo=None,
    data_evento=None,
    data_inicio=None,
    data_fim=None,
    metros_furados=0.0,
    observacoes="",
):
    return MaquinaEventoOperacional.objects.create(
        empresa_id=maquina.empresa_id,
        maquina=maquina,
        projeto=projeto,
        furo=furo,
        empregado=empregado,
        registo=registo,
        tipo_evento=tipo_evento,
        data_evento=data_evento or timezone.now().date(),
        data_inicio=data_inicio,
        data_fim=data_fim,
        metros_furados=metros_furados or 0.0,
        observacoes=observacoes or "",
    )


def registar_operacao_maquinas_por_registo(*, registo, empregado=None):
    furo = registo.furo
    if not furo:
        return 0

    maquinas = furo.maquinas.filter(empresa_id=furo.empresa_id).distinct()
    total = 0
    for maquina in maquinas:
        criar_evento_operacional_maquina(
            maquina=maquina,
            tipo_evento="operacao_turno",
            projeto=registo.projeto or furo.projeto,
            furo=furo,
            empregado=empregado or registo.empregado,
            registo=registo,
            data_evento=registo.data,
            metros_furados=float(registo.metros_furados or 0.0),
            observacoes="Evento automático gerado a partir do registo diário.",
        )
        total += 1
    return total
