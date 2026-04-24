from django.shortcuts import get_object_or_404

from projetos.models import Empregados, Furo, HistoricoConfiguracaoPerfuracao


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def _filtrar_por_empresa(queryset, empresa=None, incluir_furo=True, incluir_configuracao=False):
    if empresa is None:
        return queryset

    empresa_id = _resolver_empresa_id(empresa)
    filtros = {"empresa_id": empresa_id}

    if incluir_furo:
        filtros["furo__empresa_id"] = empresa_id

    if incluir_configuracao:
        filtros["configuracao__empresa_id"] = empresa_id

    return queryset.filter(**filtros)


def _obter_queryset_base():
    return HistoricoConfiguracaoPerfuracao.objects.select_related(
        "empregado",
        "furo",
        "alterado_por",
        "configuracao",
    )


def obter_historico_configuracao_por_empregado(empregado, empresa=None):
    queryset = _obter_queryset_base().filter(empregado=empregado)
    queryset = _filtrar_por_empresa(queryset, empresa, incluir_furo=True)

    return queryset.order_by("-criado_em")


def obter_historico_configuracao_por_furo(furo, empresa=None):
    queryset = _obter_queryset_base().filter(furo=furo)
    queryset = _filtrar_por_empresa(queryset, empresa, incluir_furo=True)

    return queryset.order_by("-criado_em")


def obter_historico_configuracao_por_configuracao(configuracao, empresa=None):
    queryset = _obter_queryset_base().filter(configuracao=configuracao)
    queryset = _filtrar_por_empresa(
        queryset,
        empresa,
        incluir_furo=False,
        incluir_configuracao=True,
    )

    return queryset.order_by("-criado_em")


def obter_historico_configuracao_por_id(pk, empresa=None):
    queryset = _obter_queryset_base()
    queryset = _filtrar_por_empresa(queryset, empresa, incluir_furo=True)

    return queryset.filter(pk=pk).first()


def obter_historico_anterior(historico, empresa=None):
    if not historico:
        return None

    queryset = _obter_queryset_base().filter(
        empregado=historico.empregado,
        furo=historico.furo,
        criado_em__lt=historico.criado_em,
    )

    queryset = _filtrar_por_empresa(queryset, empresa, incluir_furo=True)

    return queryset.order_by("-criado_em").first()


def obter_ultimo_historico_da_configuracao(configuracao, empresa=None):
    queryset = _obter_queryset_base().filter(configuracao=configuracao)
    queryset = _filtrar_por_empresa(
        queryset,
        empresa,
        incluir_furo=False,
        incluir_configuracao=True,
    )

    return queryset.order_by("-criado_em").first()


def obter_historico_configuracao_por_pk(pk):
    return get_object_or_404(_obter_queryset_base(), pk=pk)


def obter_empregado_historico_por_pk_empresa(pk, empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return get_object_or_404(Empregados, pk=pk, empresa_id=empresa_id)


def obter_furo_historico_por_pk_empresa(pk, empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return get_object_or_404(Furo, pk=pk, empresa_id=empresa_id)
