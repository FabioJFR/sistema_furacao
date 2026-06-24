from django.shortcuts import get_object_or_404

from dispositivos.models import SessaoDispositivo
from projetos.models import Empregados


def obter_empregado_autenticado(user):
    return (
        Empregados.objects.filter(user=user, aprovado=True)
        .select_related("empresa")
        .first()
    )


def obter_sessao_empresa(pk, empresa_id):
    return get_object_or_404(
        SessaoDispositivo.objects.select_related("dispositivo", "furo", "empresa", "empregado"),
        pk=pk,
        empresa_id=empresa_id,
    )


def obter_sessao_ligada_empresa(sessao_id, empresa_id):
    return get_object_or_404(
        SessaoDispositivo.objects.select_related("empresa", "furo", "dispositivo"),
        pk=sessao_id,
        empresa_id=empresa_id,
        status="ligado",
    )
