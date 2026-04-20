from django.shortcuts import get_object_or_404

from projetos.models import ConfiguracaoPerfuracaoEmpregado


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
        empregado__empresa_id=empresa_id,
    )



def _obter_queryset_base_configuracoes():
    return ConfiguracaoPerfuracaoEmpregado.objects.select_related(
        "empregado",
        "furo",
        "atualizado_por",
    )



def obter_lista_configuracoes_perfuracao_empregado(empregado, empresa=None):
    queryset = _obter_queryset_base_configuracoes().filter(empregado=empregado)
    queryset = _filtrar_configuracoes_por_empresa(queryset, empresa)

    return queryset.order_by("furo__nome")



def obter_configuracao_perfuracao(pk, empresa=None):
    queryset = _obter_queryset_base_configuracoes()
    queryset = _filtrar_configuracoes_por_empresa(queryset, empresa)

    return get_object_or_404(queryset, pk=pk)