from django.shortcuts import get_object_or_404

from geologia.models import DroneComandoOperacao, DroneOperacaoTempoReal, MissaoDroneFuro
from projetos.models import Furo


def filtrar_queryset_por_empresa(queryset, empresa=None):
    if empresa is None:
        return queryset
    return queryset.filter(empresa=empresa)


def obter_operacao_empresa(empresa):
    return get_object_or_404(DroneOperacaoTempoReal, empresa=empresa)


def obter_ou_criar_operacao_empresa(empresa):
    return DroneOperacaoTempoReal.objects.get_or_create(
        empresa=empresa,
        defaults={
            "nome_operacao": "Centro de controlo DJI Mini 4 Pro",
            "estado_conexao": "desligado",
            "alvo_altitude_m": 35.0,
        },
    )


def obter_operacao_por_bridge_key(bridge_key):
    if not bridge_key:
        return None
    return DroneOperacaoTempoReal.objects.filter(bridge_api_key=bridge_key, bridge_ativa=True).first()


def obter_furo_drone(furo_id, empresa=None):
    queryset = filtrar_queryset_por_empresa(Furo.objects.select_related("projeto"), empresa=empresa)
    return get_object_or_404(queryset, pk=furo_id)


def obter_missao_drone(pk, empresa=None):
    queryset = filtrar_queryset_por_empresa(
        MissaoDroneFuro.objects.select_related("furo", "furo__projeto"),
        empresa=empresa,
    )
    return get_object_or_404(queryset, pk=pk)


def obter_comando_operacao_drone(operacao, comando_id):
    return get_object_or_404(DroneComandoOperacao, operacao=operacao, pk=comando_id)


def obter_comandos_recentes_operacao_drone(operacao, limit=10):
    return operacao.comandos.select_related("criado_por")[:limit]


def obter_comandos_pendentes_ou_enviados_operacao(operacao):
    return (
        operacao.comandos.filter(status__in=["pendente", "enviado"])
        .order_by("criado_em")
        .values(
            "id",
            "tipo_comando",
            "status",
            "latitude_alvo",
            "longitude_alvo",
            "altitude_alvo_m",
            "payload",
            "criado_em",
        )
    )


def obter_furos_hub_drone_qs(empresa=None):
    return filtrar_queryset_por_empresa(
        Furo.objects.select_related("projeto").order_by("projeto__nome", "nome"),
        empresa=empresa,
    )


def obter_missoes_hub_drone_qs(empresa=None):
    return filtrar_queryset_por_empresa(
        MissaoDroneFuro.objects.select_related("furo", "furo__projeto").order_by("-data_voo", "-criado_em"),
        empresa=empresa,
    )


def obter_logs_relacionados_missao(missao):
    return missao.logs_geologicos.select_related("furo").order_by("intervalo_de", "intervalo_ate")


def obter_missoes_drone_recentes_furo(furo, *, empresa=None, limit=3):
    queryset = MissaoDroneFuro.objects.filter(furo=furo)
    queryset = filtrar_queryset_por_empresa(queryset, empresa=empresa)
    return queryset.order_by("-data_voo", "-criado_em")[:limit]
