from django.db import transaction

from projetos.models import ConfiguracaoPerfuracaoEmpregado, HistoricoConfiguracaoPerfuracao


CAMPOS_COMPARACAO_HISTORICO_CONFIGURACAO = [
    ("comprimento_tubo", "Tubo"),
    ("comprimento_karoutier", "Karoutier"),
    ("quantidade_karoutier", "Qtd. Karoutier"),
    ("comprimento_acrescento", "Acrescento"),
    ("quantidade_acrescento", "Qtd. Acrescento"),
    ("comprimento_calibrador", "Calibrador"),
    ("quantidade_calibrador", "Qtd. Calibrador"),
    ("comprimento_record", "Record"),
    ("quantidade_record", "Qtd. Record"),
    ("comprimento_bit", "Bit"),
    ("comprimento_caixa_mola", "Caixa de mola"),
    ("comprimento_tubo_interior", "Tubo interior"),
    ("quantidade_tubo_interior", "Qtd. Tubo interior"),
    ("comprimento_acrescento_tubo_interior", "Acrescento do tubo interior"),
    ("quantidade_acrescento_tubo_interior", "Qtd. Acrescento do tubo interior"),
    ("comprimento_cabeca_interior", "Cabeça de interior"),
]


def _aplicar_snapshot_historico(configuracao, historico, utilizador):
    configuracao.empregado = historico.empregado
    configuracao.empresa = historico.empresa
    configuracao.furo = historico.furo
    configuracao.comprimento_tubo = historico.comprimento_tubo
    configuracao.comprimento_karoutier = historico.comprimento_karoutier
    configuracao.quantidade_karoutier = historico.quantidade_karoutier or 1
    configuracao.comprimento_acrescento = historico.comprimento_acrescento
    configuracao.quantidade_acrescento = historico.quantidade_acrescento or 1
    configuracao.comprimento_calibrador = historico.comprimento_calibrador
    configuracao.quantidade_calibrador = historico.quantidade_calibrador or 1
    configuracao.comprimento_record = historico.comprimento_record
    configuracao.quantidade_record = historico.quantidade_record or 1
    configuracao.comprimento_bit = historico.comprimento_bit
    configuracao.comprimento_caixa_mola = historico.comprimento_caixa_mola
    configuracao.comprimento_tubo_interior = historico.comprimento_tubo_interior
    configuracao.quantidade_tubo_interior = historico.quantidade_tubo_interior or 1
    configuracao.comprimento_acrescento_tubo_interior = historico.comprimento_acrescento_tubo_interior
    configuracao.quantidade_acrescento_tubo_interior = historico.quantidade_acrescento_tubo_interior or 1
    configuracao.comprimento_cabeca_interior = historico.comprimento_cabeca_interior
    configuracao.atualizado_por = utilizador
    return configuracao


@transaction.atomic
def restaurar_configuracao_a_partir_historico(*, historico, utilizador):
    configuracao = historico.configuracao
    if configuracao is None:
        configuracao = ConfiguracaoPerfuracaoEmpregado()

    configuracao = _aplicar_snapshot_historico(configuracao, historico, utilizador)
    configuracao.save()

    HistoricoConfiguracaoPerfuracao.registar_historico(
        configuracao=configuracao,
        acao="editado",
        utilizador=utilizador,
        observacoes=f"Configuração restaurada a partir do histórico #{historico.pk}.",
    )
    return configuracao


def construir_comparacao_historico(*, historico_atual, historico_anterior):
    comparacao = []
    for campo, label in CAMPOS_COMPARACAO_HISTORICO_CONFIGURACAO:
        valor_atual = getattr(historico_atual, campo, None)
        valor_anterior = getattr(historico_anterior, campo, None) if historico_anterior else None
        comparacao.append(
            {
                "campo": campo,
                "label": label,
                "anterior": valor_anterior,
                "atual": valor_atual,
                "alterado": valor_atual != valor_anterior,
            }
        )
    return comparacao
