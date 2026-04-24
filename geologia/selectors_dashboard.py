from pathlib import Path

from django.shortcuts import get_object_or_404

from geologia.models import (
    ComandoDroneSFOperacao,
    ConfiguracaoDroneSF,
    DroneSF,
    LogGeologicoFuro,
    MissaoDroneFuro,
    MissaoProgramadaDroneSF,
    OperacaoDroneSFTempoReal,
)
from projetos.models import Furo


def filtrar_queryset_por_empresa(queryset, empresa=None):
    if empresa is None:
        return queryset
    return queryset.filter(empresa=empresa)


def obter_furos_geologia_hub_qs(empresa=None):
    return filtrar_queryset_por_empresa(
        Furo.objects.select_related("projeto").order_by("projeto__nome", "nome"),
        empresa=empresa,
    )


def obter_logs_geologia_hub_qs(empresa=None):
    return filtrar_queryset_por_empresa(
        LogGeologicoFuro.objects.select_related("furo", "furo__projeto").order_by("-data_registo", "-criado_em"),
        empresa=empresa,
    )


def obter_missoes_geologia_hub_qs(empresa=None):
    return filtrar_queryset_por_empresa(
        MissaoDroneFuro.objects.select_related("furo", "furo__projeto").order_by("-data_voo", "-criado_em"),
        empresa=empresa,
    )


def obter_drones_sf_hub_qs(empresa=None):
    return filtrar_queryset_por_empresa(
        DroneSF.objects.prefetch_related("modulos", "sensores").order_by("nome"),
        empresa=empresa,
    )


def listar_documentos_knowledge_base_drone():
    knowledge_root = Path(__file__).resolve().parents[1] / "knowledge_base" / "drone"
    documentos_drone = []
    if knowledge_root.exists():
        for path in sorted(knowledge_root.iterdir()):
            if path.is_file():
                documentos_drone.append(
                    {
                        "nome": path.name,
                        "relativo": str(path.relative_to(knowledge_root.parent.parent)),
                    }
                )
    return documentos_drone


def obter_drone_sf(pk, empresa=None):
    qs = filtrar_queryset_por_empresa(
        DroneSF.objects.prefetch_related("modulos", "sensores"),
        empresa=empresa,
    )
    return get_object_or_404(qs, pk=pk)


def obter_drone_sf_simples(pk, empresa=None):
    qs = filtrar_queryset_por_empresa(DroneSF.objects.all(), empresa=empresa)
    return get_object_or_404(qs, pk=pk)


def obter_ou_criar_configuracao_drone_sf(drone):
    return ConfiguracaoDroneSF.objects.get_or_create(
        drone=drone,
        defaults={"empresa": drone.empresa},
    )


def obter_ou_criar_operacao_drone_sf(drone):
    return OperacaoDroneSFTempoReal.objects.get_or_create(
        drone=drone,
        defaults={"empresa": drone.empresa, "bridge_nome": "Bridge S_F"},
    )


def obter_operacao_drone_sf(drone):
    return get_object_or_404(OperacaoDroneSFTempoReal, drone=drone, empresa=drone.empresa)


def obter_comandos_recentes_operacao_sf(operacao, limit=10):
    return operacao.comandos.select_related("criado_por")[:limit]


def obter_comandos_pendentes_ou_enviados_operacao_sf(operacao):
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


def obter_operacao_sf_por_bridge_key(bridge_key):
    if not bridge_key:
        return None
    return OperacaoDroneSFTempoReal.objects.filter(bridge_api_key=bridge_key, bridge_ativa=True).first()


def obter_missao_programada_drone_sf(drone, missao_id):
    return get_object_or_404(
        MissaoProgramadaDroneSF,
        drone=drone,
        empresa=drone.empresa,
        pk=missao_id,
    )


def obter_comando_sf_operacao(operacao, comando_id):
    return get_object_or_404(ComandoDroneSFOperacao, operacao=operacao, pk=comando_id)


def obter_furo_geologia_dashboard(furo_id, empresa=None):
    qs = filtrar_queryset_por_empresa(Furo.objects.select_related("projeto"), empresa=empresa)
    return get_object_or_404(qs, pk=furo_id)


def obter_logs_furo_geologia(furo):
    return (
        furo.logs_geologicos.select_related("medicao", "missao_drone")
        .prefetch_related("anexos")
        .order_by("intervalo_de", "intervalo_ate", "-criado_em")
    )


def obter_missoes_furo_geologia(furo):
    return furo.missoes_drone_geologia.all().order_by("-data_voo", "-criado_em")
