from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from geologia.models import ComandoDroneSFOperacao, MissaoProgramadaDroneSF, OperacaoDroneSFTempoReal


def _resolver_momento_agendado_local(missao, referencia_local):
    data_base = referencia_local.date()
    if missao.tipo_frequencia == "semanal" and missao.dia_semana is not None:
        dias_ate_execucao = (missao.dia_semana - data_base.weekday()) % 7
        data_base = data_base + timedelta(days=dias_ate_execucao)
    agendado_naive = datetime.combine(data_base, missao.hora_execucao)
    return timezone.make_aware(agendado_naive, timezone.get_current_timezone())


def _missao_esta_em_janela_execucao(missao, agora_local):
    momento_agendado = _resolver_momento_agendado_local(missao, agora_local)
    if agora_local < momento_agendado:
        return False, momento_agendado

    ultima_execucao = timezone.localtime(missao.ultima_execucao_em) if missao.ultima_execucao_em else None

    if missao.tipo_frequencia == "diaria":
        if ultima_execucao and ultima_execucao.date() == agora_local.date() and ultima_execucao >= momento_agendado:
            return False, momento_agendado
    elif missao.tipo_frequencia == "semanal":
        inicio_semana = agora_local.date() - timedelta(days=agora_local.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        if ultima_execucao and inicio_semana <= ultima_execucao.date() <= fim_semana and ultima_execucao >= momento_agendado:
            return False, momento_agendado
    elif missao.tipo_frequencia == "pontual":
        if ultima_execucao is not None:
            return False, momento_agendado

    return True, momento_agendado


def _payload_missao(missao, momento_agendado):
    return {
        "origem": "motor_missoes_programadas_drone_sf",
        "missao_programada_id": str(missao.id),
        "missao_programada_nome": missao.nome,
        "agendada_para": momento_agendado.isoformat(),
        "gravar_video": missao.gravar_video,
        "captar_foto": missao.captar_foto,
        "pairar_no_destino": missao.pairar_no_destino,
        "regressar_base": missao.regressar_base,
        "ativar_sensores": missao.ativar_sensores,
        "usar_live_view": missao.usar_live_view,
        "notas": missao.notas,
    }


def _guardar_resumo_operacao(operacao, resumo_operacao, agora):
    if operacao is None:
        return
    metadados = dict(operacao.metadados or {})
    metadados["motor_missoes_programadas"] = {
        "ultima_execucao_em": agora.isoformat(),
        "processadas": resumo_operacao["processadas"],
        "executadas": resumo_operacao["executadas"],
        "ignoradas": resumo_operacao["ignoradas"],
        "desativadas": resumo_operacao["desativadas"],
        "sem_operacao": resumo_operacao["sem_operacao"],
        "ultimo_erro": resumo_operacao.get("ultimo_erro", ""),
        "ultimas_missoes_disparadas": resumo_operacao.get("ultimas_missoes_disparadas", [])[:5],
        "ultimos_comandos_gerados": resumo_operacao.get("ultimos_comandos_gerados", [])[:5],
    }
    operacao.metadados = metadados
    operacao.save(update_fields=["metadados", "atualizado_em"])


@transaction.atomic
def processar_missoes_programadas_drone_sf(*, empresa=None, agora=None, utilizador=None):
    agora = agora or timezone.now()
    agora_local = timezone.localtime(agora)

    qs = MissaoProgramadaDroneSF.objects.select_related("drone", "empresa").filter(ativa=True)
    if empresa is not None:
        empresa_id = getattr(empresa, "pk", empresa)
        qs = qs.filter(empresa_id=empresa_id)

    resumo = {
        "processadas": 0,
        "executadas": 0,
        "ignoradas": 0,
        "desativadas": 0,
        "sem_operacao": 0,
        "comandos_ids": [],
        "missoes_ids": [],
    }
    resumo_por_operacao = {}

    for missao in qs.order_by("hora_execucao", "nome"):
        resumo["processadas"] += 1
        deve_executar, momento_agendado = _missao_esta_em_janela_execucao(missao, agora_local)
        if not deve_executar:
            resumo["ignoradas"] += 1
            operacao_existente = OperacaoDroneSFTempoReal.objects.filter(drone=missao.drone, empresa=missao.empresa).first()
            if operacao_existente:
                item = resumo_por_operacao.setdefault(
                    operacao_existente.pk,
                    {
                        "operacao": operacao_existente,
                        "processadas": 0,
                        "executadas": 0,
                        "ignoradas": 0,
                        "desativadas": 0,
                        "sem_operacao": 0,
                        "ultimo_erro": "",
                        "ultimas_missoes_disparadas": [],
                        "ultimos_comandos_gerados": [],
                    },
                )
                item["processadas"] += 1
                item["ignoradas"] += 1
            continue

        operacao = OperacaoDroneSFTempoReal.objects.filter(drone=missao.drone, empresa=missao.empresa).first()
        if operacao is None:
            resumo["sem_operacao"] += 1
            continue
        item = resumo_por_operacao.setdefault(
            operacao.pk,
            {
                "operacao": operacao,
                "processadas": 0,
                "executadas": 0,
                "ignoradas": 0,
                "desativadas": 0,
                "sem_operacao": 0,
                "ultimo_erro": "",
                "ultimas_missoes_disparadas": [],
                "ultimos_comandos_gerados": [],
            },
        )
        item["processadas"] += 1

        comando = ComandoDroneSFOperacao.objects.create(
            operacao=operacao,
            empresa=missao.empresa,
            criado_por=utilizador,
            tipo_comando="goto",
            latitude_alvo=missao.latitude_alvo,
            longitude_alvo=missao.longitude_alvo,
            altitude_alvo_m=missao.altitude_alvo_m,
            payload=_payload_missao(missao, momento_agendado),
        )

        missao.ultima_execucao_em = agora
        campos_update = ["ultima_execucao_em", "atualizado_em"]
        if missao.tipo_frequencia == "pontual":
            missao.ativa = False
            campos_update.append("ativa")
            resumo["desativadas"] += 1
        missao.save(update_fields=campos_update)

        resumo["executadas"] += 1
        item["executadas"] += 1
        resumo["comandos_ids"].append(str(comando.id))
        resumo["missoes_ids"].append(str(missao.id))
        item["ultimas_missoes_disparadas"].insert(
            0,
            {
                "nome": missao.nome,
                "origem": "Automática",
                "timestamp": agora.isoformat(),
            },
        )
        item["ultimos_comandos_gerados"].insert(
            0,
            {
                "tipo": comando.get_tipo_comando_display(),
                "status": comando.get_status_display(),
                "origem": "Automática",
                "timestamp": agora.isoformat(),
            },
        )
        if missao.tipo_frequencia == "pontual":
            item["desativadas"] += 1

    for item in resumo_por_operacao.values():
        _guardar_resumo_operacao(item["operacao"], item, agora)

    return resumo
