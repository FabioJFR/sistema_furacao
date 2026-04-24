from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum

from projetos.models import Furo
from projetos.models import (
    Despesa,
    Empregados,
    EventoAnalytics,
    Maquina,
    Material,
    Medicao,
    Projeto,
    RegistoDiarioEmpregado,
)

from inspecao_ai.models import ChatSessaoAI


def listar_sessoes_chat_ativas_empresa(empresa, limit=12):
    return ChatSessaoAI.objects.filter(empresa=empresa, ativa=True).prefetch_related("mensagens")[:limit]


def obter_sessao_chat_empresa(sessao_id, empresa):
    return get_object_or_404(ChatSessaoAI, pk=sessao_id, empresa=empresa)


def obter_furo_contexto_chat(empresa, furo_contexto_id):
    if not furo_contexto_id:
        return None
    return Furo.objects.filter(empresa=empresa, pk=furo_contexto_id).select_related("projeto").first()


def obter_projetos_empresa_qs(empresa):
    return Projeto.objects.filter(empresa=empresa)


def obter_furos_empresa_qs(empresa):
    return Furo.objects.filter(empresa=empresa)


def obter_empregados_empresa_qs(empresa):
    return Empregados.objects.filter(empresa=empresa)


def obter_maquinas_empresa_qs(empresa):
    return Maquina.objects.filter(empresa=empresa)


def obter_materiais_empresa_qs(empresa):
    return Material.objects.filter(empresa=empresa)


def obter_despesas_empresa_qs(empresa):
    return Despesa.objects.filter(empresa=empresa)


def listar_materiais_baixo_stock(materiais_qs, limit=5):
    materiais_baixo_stock = list(
        materiais_qs.filter(quantidade__lte=0).values_list("nome", flat=True)[:limit]
    ) + list(
        materiais_qs.extra(where=["quantidade <= stock_minimo"]).values_list("nome", flat=True)[:limit]
    )
    return list(dict.fromkeys(materiais_baixo_stock))


def listar_maquinas_alerta(maquinas_qs, limit=8):
    return list(maquinas_qs.exclude(estado="operacional").values("nome", "estado")[:limit])


def obter_total_despesas_empresa(despesas_qs):
    return despesas_qs.aggregate(total=Sum("valor")).get("total") or 0


def listar_despesas_top_categorias(despesas_qs, limit=5):
    return list(despesas_qs.values("categoria").annotate(total=Sum("valor")).order_by("-total")[:limit])


def listar_eventos_recentes_values(empresa, limit=5):
    return list(
        EventoAnalytics.objects.filter(empresa=empresa)
        .values("entidade_tipo", "tipo_evento", "entidade_label", "criado_em")
        .order_by("-criado_em")[:limit]
    )


def contar_medicoes_empresa(empresa):
    return Medicao.objects.filter(empresa=empresa).count()


def contar_registos_empresa(empresa):
    return RegistoDiarioEmpregado.objects.filter(empresa=empresa).count()


def listar_maquinas_estados(maquinas_qs):
    return list(maquinas_qs.values("estado").annotate(total=Count("id")).order_by("estado"))


def listar_nomes_furos_empresa(empresa):
    return list(Furo.objects.filter(empresa=empresa).values_list("nome", flat=True))


def obter_furo_empresa_por_nome(empresa, nome, *, include_projeto=False):
    queryset = Furo.objects.filter(empresa=empresa, nome__iexact=nome)
    if include_projeto:
        queryset = queryset.select_related("projeto")
    return queryset.first()


def obter_total_despesas_furo(furo):
    return float(Despesa.objects.filter(furo=furo).aggregate(total=Sum("valor")).get("total") or 0)


def listar_eventos_empresa(empresa, limit=8):
    return EventoAnalytics.objects.filter(empresa=empresa).order_by("-criado_em")[:limit]


def listar_candidatos_furos_relacionados(empresa, furo_base):
    return Furo.objects.filter(empresa=empresa).exclude(pk=furo_base.pk).select_related("projeto")


def listar_furos_memoria_empresa(empresa, limite=12):
    return (
        Furo.objects.filter(empresa=empresa)
        .select_related("projeto")
        .order_by("-data")[:limite]
    )
