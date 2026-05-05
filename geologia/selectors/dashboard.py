from pathlib import Path

from django.shortcuts import get_object_or_404
from django.utils import timezone

from geologia.models import (
    ComandoDroneSFOperacao,
    ConfiguracaoDroneSF,
    DroneSF,
    LogGeologicoFuro,
    MissaoDroneFuro,
    MissaoProgramadaDroneSF,
    OperacaoDroneSFTempoReal,
)
from plataforma.services.empresas import normalizar_geologia_score_config
from projetos.models import Furo


PESOS_PRIORIDADE_GEOLOGIA_DEFAULT = {
    "sem_logs": 12,
    "conflito_intervalo": 9,
    "pendente_validacao": 3,
    "sem_anexo": 1,
    "sem_log_24h": 4,
    "sem_log_48h": 7,
}

JANELAS_RECENCIA_HORAS_DEFAULT = {
    "atencao": 24,
    "critico": 48,
}


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


def obter_semoforo_e_prioridades_furos_geologo(empresa=None, *, limite_top=5):
    """Calcula semáforo de qualidade por furo e devolve ranking de prioridade.

    Regras iniciais (simples e operacionais):
    - vermelho: sem logs, conflito de intervalo, ou log mais recente com >48h.
    - amarelo: pendências de validação/anexos em falta ou log mais recente com >24h.
    - verde: sem sinais críticos.
    """
    furos = list(obter_furos_geologia_hub_qs(empresa=empresa))
    logs = list(obter_logs_geologia_hub_qs(empresa=empresa))

    config_empresa = normalizar_geologia_score_config(getattr(empresa, "geologia_score_config", {}) if empresa else {})
    pesos_cfg = config_empresa["pesos"] if config_empresa else PESOS_PRIORIDADE_GEOLOGIA_DEFAULT
    janelas_cfg = config_empresa["janelas_horas"] if config_empresa else JANELAS_RECENCIA_HORAS_DEFAULT

    agora = timezone.now()
    limite_24h = agora - timezone.timedelta(hours=janelas_cfg["atencao"])
    limite_48h = agora - timezone.timedelta(hours=janelas_cfg["critico"])

    logs_por_furo = {}
    for log in logs:
        logs_por_furo.setdefault(log.furo_id, []).append(log)

    semaforo_furos = []
    for furo in furos:
        logs_furo = logs_por_furo.get(furo.id, [])
        total_logs = len(logs_furo)
        ultimo_log = logs_furo[0] if logs_furo else None

        pendentes_validacao = 0
        anexos_em_falta = 0
        conflitos_intervalo = 0
        sem_log_recente_24h = False
        sem_log_recente_48h = False

        if not logs_furo:
            sem_log_recente_24h = True
            sem_log_recente_48h = True
        else:
            pendentes_validacao = sum(1 for l in logs_furo if l.status_validacao == "pendente")
            anexos_em_falta = sum(1 for l in logs_furo if not l.anexos.exists())

            # Conflito de intervalo real (sobreposição estrita).
            ordenados = sorted(logs_furo, key=lambda l: (l.intervalo_de, l.intervalo_ate, l.criado_em))
            for idx, atual in enumerate(ordenados):
                for prox in ordenados[idx + 1:]:
                    if prox.intervalo_de >= atual.intervalo_ate:
                        break
                    if atual.intervalo_de < prox.intervalo_ate and prox.intervalo_de < atual.intervalo_ate:
                        conflitos_intervalo += 1

            ultimo_ts = ultimo_log.atualizado_em if ultimo_log and ultimo_log.atualizado_em else None
            if ultimo_ts:
                sem_log_recente_24h = ultimo_ts < limite_24h
                sem_log_recente_48h = ultimo_ts < limite_48h

        score = 0
        if total_logs == 0:
            score += pesos_cfg["sem_logs"]
        score += conflitos_intervalo * pesos_cfg["conflito_intervalo"]
        score += pendentes_validacao * pesos_cfg["pendente_validacao"]
        score += anexos_em_falta * pesos_cfg["sem_anexo"]
        if sem_log_recente_48h:
            score += pesos_cfg["sem_log_48h"]
        elif sem_log_recente_24h:
            score += pesos_cfg["sem_log_24h"]

        if total_logs == 0 or conflitos_intervalo > 0 or sem_log_recente_48h:
            estado = "vermelho"
            estado_label = "Crítico"
        elif pendentes_validacao > 0 or anexos_em_falta > 0 or sem_log_recente_24h:
            estado = "amarelo"
            estado_label = "Atenção"
        else:
            estado = "verde"
            estado_label = "OK"

        semaforo_furos.append(
            {
                "furo": furo,
                "projeto": furo.projeto,
                "estado": estado,
                "estado_label": estado_label,
                "score": score,
                "total_logs": total_logs,
                "ultimo_log": ultimo_log,
                "pendentes_validacao": pendentes_validacao,
                "conflitos_intervalo": conflitos_intervalo,
                "anexos_em_falta": anexos_em_falta,
                "sem_log_recente_24h": sem_log_recente_24h,
                "sem_log_recente_48h": sem_log_recente_48h,
            }
        )

    top_prioritarios = sorted(semaforo_furos, key=lambda x: x["score"], reverse=True)[:limite_top]
    metadados_score = {
        "pesos": pesos_cfg,
        "janelas_horas": janelas_cfg,
    }
    return semaforo_furos, top_prioritarios, metadados_score
