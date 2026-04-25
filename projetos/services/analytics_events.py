from projetos.models import EventoAnalytics


def criar_evento_analytics(*, user, contexto, instance, tipo_evento, actor_tipo, snapshot_antes, snapshot_depois, metricas):
    EventoAnalytics.objects.create(
        actor_user=user if getattr(user, "is_authenticated", False) else None,
        actor_username=getattr(user, "username", "") if user else "",
        actor_tipo=actor_tipo,
        empresa_id=contexto["empresa_id"],
        projeto_id=contexto["projeto_id"],
        furo_id=contexto["furo_id"],
        empregado_id=contexto["empregado_id"],
        material_id=contexto["material_id"],
        maquina_id=contexto["maquina_id"],
        tipo_evento=tipo_evento,
        entidade_tipo=instance.__class__.__name__,
        entidade_id=str(instance.pk),
        entidade_label=str(instance),
        snapshot_antes=snapshot_antes,
        snapshot_depois=snapshot_depois,
        metricas=metricas,
    )
