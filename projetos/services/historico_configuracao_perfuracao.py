from django.db import transaction

from projetos.models import ConfiguracaoPerfuracaoEmpregado, HistoricoConfiguracaoPerfuracao


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
