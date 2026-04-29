from django.shortcuts import get_object_or_404

from dispositivos.models import ImportacaoDispositivoHistorico


def listar_historico_importacoes_qs(empresa_id=None):
    qs = ImportacaoDispositivoHistorico.objects.select_related("sessao", "empresa", "utilizador")
    if empresa_id:
        qs = qs.filter(empresa_id=empresa_id)
    return qs


def obter_historico_importacao(pk, empresa_id=None):
    qs = listar_historico_importacoes_qs(empresa_id=empresa_id)
    return get_object_or_404(qs, pk=pk)
