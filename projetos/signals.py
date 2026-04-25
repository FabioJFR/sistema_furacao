from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from django.core.files.base import File
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from inspecao_ai.models import AnaliseImagemAI, ChatMensagemAI, ChatSessaoAI, DeteccaoImagemAI
from projetos.selectors.analytics_events import obter_instancia_original
from projetos.services.analytics_events import criar_evento_analytics
from projetos.models import (
    DevolucaoMaterial,
    Despesa,
    EmpregadoFuro,
    EmpregadoProjeto,
    Furo,
    LevantamentoMaterial,
    Maquina,
    Material,
    Medicao,
    Projeto,
    RegistoDiarioEmpregado,
)
from projetos.request_context import get_current_user


TRACKED_MODELS = (
    Projeto,
    Furo,
    EmpregadoProjeto,
    EmpregadoFuro,
    Medicao,
    RegistoDiarioEmpregado,
    Material,
    LevantamentoMaterial,
    DevolucaoMaterial,
    Maquina,
    Despesa,
    AnaliseImagemAI,
    DeteccaoImagemAI,
    ChatSessaoAI,
    ChatMensagemAI,
)


def _coerce(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, File):
        return str(value) if getattr(value, "name", "") else None
    return value


def _snapshot(instance):
    data = {}
    for field in instance._meta.fields:
        if getattr(field, "is_relation", False) and getattr(field, "many_to_one", False):
            data[field.name] = _coerce(getattr(instance, field.attname, None))
        else:
            data[field.name] = _coerce(getattr(instance, field.name, None))
    return data


def _metricas(instance):
    metricas = {}
    for field_name in [
        "metros_furados",
        "metros_furados_hoje",
        "metros_furados_mes",
        "profundidade_atual",
        "profundidade_inicial",
        "profundidade_alvo_inicial",
        "profundidade_alvo_atual",
        "profundidade_maxima_atingida",
        "profundidade_medida",
        "profundidade_furo_antes",
        "profundidade_furo_depois",
        "quantidade",
        "stock_minimo",
        "valor",
        "km",
        "horimetro",
        "horas_trabalhadas",
        "horas_paragem",
    ]:
        if hasattr(instance, field_name):
            metricas[field_name] = _coerce(getattr(instance, field_name, None))
    return {k: v for k, v in metricas.items() if v is not None}


def _actor_tipo(user):
    if not user or not getattr(user, "is_authenticated", False):
        return ""
    if user.is_superuser:
        return "superuser"
    if hasattr(user, "empregado"):
        return "empregado"
    return "empresa"


def _contexto_relacional(instance):
    empresa_id = getattr(instance, "empresa_id", None)
    projeto_id = getattr(instance, "projeto_id", None)
    furo_id = getattr(instance, "furo_id", None)
    empregado_id = getattr(instance, "empregado_id", None)
    material_id = getattr(instance, "material_id", None)
    maquina_id = getattr(instance, "maquina_id", None)
    sessao = getattr(instance, "sessao", None)

    furo = getattr(instance, "furo", None)
    projeto = getattr(instance, "projeto", None)
    empregado = getattr(instance, "empregado", None)
    material = getattr(instance, "material", None)
    maquina = getattr(instance, "maquina", None)

    if empresa_id is None:
        empresa_id = (
            getattr(projeto, "empresa_id", None)
            or getattr(furo, "empresa_id", None)
            or getattr(empregado, "empresa_id", None)
            or getattr(material, "empresa_id", None)
            or getattr(maquina, "empresa_id", None)
            or getattr(sessao, "empresa_id", None)
        )

    if projeto_id is None:
        projeto_id = (
            getattr(furo, "projeto_id", None)
            or getattr(material, "projeto_id", None)
            or getattr(maquina, "projeto_atual_id", None)
        )

    if furo_id is None:
        furo_id = getattr(material, "furo_id", None)

    return {
        "empresa_id": empresa_id,
        "projeto_id": projeto_id,
        "furo_id": furo_id,
        "empregado_id": empregado_id,
        "material_id": material_id,
        "maquina_id": maquina_id,
    }


def _criar_evento(instance, tipo_evento):
    user = get_current_user()
    contexto = _contexto_relacional(instance)
    criar_evento_analytics(
        user=user,
        contexto=contexto,
        instance=instance,
        tipo_evento=tipo_evento,
        actor_tipo=_actor_tipo(user),
        snapshot_antes=getattr(instance, "_analytics_snapshot_antes", {}) or {},
        snapshot_depois={} if tipo_evento == "delete" else _snapshot(instance),
        metricas=_metricas(instance),
    )


@receiver(pre_save)
def analytics_pre_save(sender, instance, **kwargs):
    if sender not in TRACKED_MODELS or not getattr(instance, "pk", None):
        return
    original = obter_instancia_original(sender, instance.pk)
    instance._analytics_snapshot_antes = _snapshot(original) if original else {}


@receiver(post_save)
def analytics_post_save(sender, instance, created, **kwargs):
    if sender not in TRACKED_MODELS:
        return
    instance._analytics_snapshot_antes = getattr(instance, "_analytics_snapshot_antes", {})
    _criar_evento(instance, "create" if created else "update")


@receiver(pre_delete)
def analytics_pre_delete(sender, instance, **kwargs):
    if sender not in TRACKED_MODELS:
        return
    instance._analytics_snapshot_antes = _snapshot(instance)
    _criar_evento(instance, "delete")
