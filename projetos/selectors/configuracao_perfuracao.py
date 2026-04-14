from django.shortcuts import get_object_or_404

from projetos.models import ConfiguracaoPerfuracaoEmpregado


def obter_lista_configuracoes_perfuracao_empregado(empregado):
    return ConfiguracaoPerfuracaoEmpregado.objects.filter(
        empregado=empregado
    ).select_related("furo", "atualizado_por").order_by("furo__nome")


def obter_configuracao_perfuracao(pk):
    return get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado.objects.select_related(
            "empregado", "furo", "atualizado_por"
        ),
        pk=pk
    )