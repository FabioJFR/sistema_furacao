from django.shortcuts import get_object_or_404

from projetos.models import ConfiguracaoPerfuracaoEmpregado, EmpregadoFuro, Empregados, RegistoDiarioEmpregado


# TODO futuro:
# - centralizar filtros multiempresa num helper/base selector reutilizável
# - avaliar paginação/otimização se o volume de configurações crescer
# - considerar cache em consultas muito frequentes


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _filtrar_configuracoes_por_empresa(queryset, empresa=None):
    if empresa is None:
        return queryset

    empresa_id = _resolver_empresa_id(empresa)
    return queryset.filter(
        empresa_id=empresa_id,
        furo__empresa_id=empresa_id,
    )



def _obter_queryset_base_configuracoes():
    return ConfiguracaoPerfuracaoEmpregado.objects.select_related(
        "empregado",
        "furo",
        "atualizado_por",
    )



def obter_lista_configuracoes_perfuracao_empregado(empregado, empresa=None):
    furo_ids_associados = EmpregadoFuro.objects.filter(empregado=empregado).values_list("furo_id", flat=True)
    furo_ids_registos = RegistoDiarioEmpregado.objects.filter(
        empregado=empregado,
        furo__isnull=False,
    ).values_list("furo_id", flat=True)
    queryset = _obter_queryset_base_configuracoes().filter(
        furo_id__in=list(furo_ids_associados) + list(furo_ids_registos)
    )
    queryset = _filtrar_configuracoes_por_empresa(queryset, empresa)

    return queryset.order_by("furo__nome")



def obter_configuracao_perfuracao(pk, empresa=None):
    queryset = _obter_queryset_base_configuracoes()
    queryset = _filtrar_configuracoes_por_empresa(queryset, empresa)

    return get_object_or_404(queryset, pk=pk)


def obter_empregado_por_pk_empresa(pk, empresa):
    empresa_id = _resolver_empresa_id(empresa)
    return get_object_or_404(Empregados, pk=pk, empresa_id=empresa_id)


def obter_configuracao_perfuracao_empregado(pk, empregado):
    furo_ids_associados = EmpregadoFuro.objects.filter(empregado=empregado).values_list("furo_id", flat=True)
    furo_ids_registos = RegistoDiarioEmpregado.objects.filter(
        empregado=empregado,
        furo__isnull=False,
    ).values_list("furo_id", flat=True)
    return get_object_or_404(
        _obter_queryset_base_configuracoes(),
        pk=pk,
        empresa=empregado.empresa,
        furo_id__in=list(furo_ids_associados) + list(furo_ids_registos),
    )


def obter_configuracao_perfuracao_furo_empregado(furo, empregado):
    return (
        _obter_queryset_base_configuracoes()
        .filter(
            furo=furo,
            empresa=empregado.empresa,
        )
        .first()
    )


def obter_configuracao_perfuracao_admin(pk, empresa):
    queryset = _obter_queryset_base_configuracoes()
    queryset = _filtrar_configuracoes_por_empresa(queryset, empresa)
    return get_object_or_404(queryset, pk=pk)
