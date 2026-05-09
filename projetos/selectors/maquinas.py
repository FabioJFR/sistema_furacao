from django.shortcuts import get_object_or_404
from django.db.models import Sum

from projetos.models import Maquina, MaquinaAvaria, MaquinaEventoOperacional, MaquinaTurno



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _filtrar_por_empresa(queryset, empresa=None, campo="empresa_id"):
    if empresa is None:
        return queryset

    empresa_id = _resolver_empresa_id(empresa)
    return queryset.filter(**{campo: empresa_id})



def _obter_queryset_base_maquinas():
    return (
        Maquina.objects.select_related("projeto_atual")
        .prefetch_related("projetos", "furos", "turnos_maquina")
    )



def obter_lista_maquinas(empresa=None):
    queryset = _obter_queryset_base_maquinas().order_by("nome")
    return _filtrar_por_empresa(queryset, empresa)



def obter_maquina(maquina_id, empresa=None):
    queryset = _obter_queryset_base_maquinas()
    queryset = _filtrar_por_empresa(queryset, empresa)
    return get_object_or_404(queryset, pk=maquina_id)


def obter_maquina_turno(turno_id, *, maquina=None, empresa=None):
    queryset = MaquinaTurno.objects.select_related("maquina")
    if maquina is not None:
        queryset = queryset.filter(maquina=maquina)
    if empresa is not None:
        empresa_id = _resolver_empresa_id(empresa)
        queryset = queryset.filter(maquina__empresa_id=empresa_id)
    return get_object_or_404(queryset, pk=turno_id)



def obter_contexto_maquina_detail(maquina_id, empresa=None):
    maquina = obter_maquina(maquina_id, empresa=empresa)

    projetos = maquina.projetos.all()
    furos = maquina.furos.all()

    if empresa is not None:
        empresa_id = _resolver_empresa_id(empresa)
        projetos = projetos.filter(empresa_id=empresa_id)
        furos = furos.filter(empresa_id=empresa_id)
        avarias = MaquinaAvaria.objects.filter(maquina=maquina, empresa_id=empresa_id)
        eventos = MaquinaEventoOperacional.objects.filter(maquina=maquina, empresa_id=empresa_id)
    else:
        avarias = MaquinaAvaria.objects.filter(maquina=maquina)
        eventos = MaquinaEventoOperacional.objects.filter(maquina=maquina)

    total_metros_realizados = (
        eventos.filter(tipo_evento="operacao_turno").aggregate(total=Sum("metros_furados")).get("total") or 0.0
    )
    trabalhadores_ids = (
        eventos.filter(empregado__isnull=False)
        .values_list("empregado_id", flat=True)
        .distinct()
    )
    turnos_maquina = sorted(maquina.turnos_maquina.all(), key=lambda item: (item.ordem_turno, item.hora_inicio, item.hora_fim))

    return {
        "maquina": maquina,
        "projetos": projetos,
        "furos": furos,
        "turnos_maquina": turnos_maquina,
        "avarias": avarias.order_by("-data_inicio"),
        "eventos_operacionais": eventos.order_by("-data_evento", "-criado_em")[:100],
        "total_metros_realizados_maquina": round(float(total_metros_realizados), 2),
        "total_trabalhadores_maquina": trabalhadores_ids.count(),
    }
