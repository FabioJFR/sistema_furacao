from projetos.models import HistoricoConfiguracaoPerfuracao


def obter_historico_configuracao_por_empregado(empregado):
    return (
        HistoricoConfiguracaoPerfuracao.objects
        .filter(empregado=empregado)
        .select_related("furo", "alterado_por", "configuracao")
        .order_by("-criado_em")
    )


def obter_historico_configuracao_por_furo(furo):
    return (
        HistoricoConfiguracaoPerfuracao.objects
        .filter(furo=furo)
        .select_related("empregado", "alterado_por", "configuracao")
        .order_by("-criado_em")
    )


def obter_historico_configuracao_por_configuracao(configuracao):
    return (
        HistoricoConfiguracaoPerfuracao.objects
        .filter(configuracao=configuracao)
        .select_related("empregado", "furo", "alterado_por", "configuracao")
        .order_by("-criado_em")
    )


def obter_historico_configuracao_por_id(pk):
    return (
        HistoricoConfiguracaoPerfuracao.objects
        .select_related("empregado", "furo", "alterado_por", "configuracao")
        .filter(pk=pk)
        .first()
    )


def obter_historico_anterior(historico):
    if not historico:
        return None

    queryset = HistoricoConfiguracaoPerfuracao.objects.filter(
        empregado=historico.empregado,
        furo=historico.furo,
        criado_em__lt=historico.criado_em,
    ).order_by("-criado_em")

    return queryset.first()


def obter_ultimo_historico_da_configuracao(configuracao):
    return (
        HistoricoConfiguracaoPerfuracao.objects
        .filter(configuracao=configuracao)
        .select_related("alterado_por", "empregado", "furo")
        .order_by("-criado_em")
        .first()
    )