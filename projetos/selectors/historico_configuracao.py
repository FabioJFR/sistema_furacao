from django.shortcuts import get_object_or_404

from projetos.models import EmpregadoFuro, Empregados, Furo, HistoricoConfiguracaoPerfuracao, RegistoDiarioEmpregado


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
    furo_ids_associados = EmpregadoFuro.objects.filter(empregado=empregado).values_list("furo_id", flat=True)
    furo_ids_registos = RegistoDiarioEmpregado.objects.filter(
        empregado=empregado,
        furo__isnull=False,
    ).values_list("furo_id", flat=True)
    queryset = _obter_queryset_base().filter(
        furo_id__in=list(furo_ids_associados) + list(furo_ids_registos)
    )
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
