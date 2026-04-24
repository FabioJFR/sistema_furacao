from django.db import transaction

from projetos.models import HistoricoConfiguracaoPerfuracao


@transaction.atomic
def guardar_configuracao_perfuracao(
    *,
    form,
    empregado,
    empresa,
    atualizado_por,
    acao_historico,
    observacoes_historico,
):
    configuracao = form.save(commit=False)
    configuracao.empregado = empregado
    configuracao.empresa = empresa
    configuracao.atualizado_por = atualizado_por
    configuracao.save()

    HistoricoConfiguracaoPerfuracao.registar_historico(
        configuracao=configuracao,
        acao=acao_historico,
        utilizador=atualizado_por,
        observacoes=observacoes_historico,
    )
    return configuracao


@transaction.atomic
def apagar_configuracao_perfuracao(*, configuracao, utilizador, observacoes_historico):
    HistoricoConfiguracaoPerfuracao.registar_historico(
        configuracao=configuracao,
        acao="apagado",
        utilizador=utilizador,
        observacoes=observacoes_historico,
    )
    configuracao_id = configuracao.id
    configuracao.delete()
    return configuracao_id
