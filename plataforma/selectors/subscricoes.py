from plataforma.models import SubscricaoEmpresa


def listar_subscricoes():
    return (
        SubscricaoEmpresa.objects
        .select_related("empresa", "plano")
        .order_by("estado", "-data_inicio", "-criado_em")
    )


def obter_metricas_subscricoes(subscricoes):
    return {
        "total_subscricoes": subscricoes.count(),
        "subscricoes_ativas": subscricoes.filter(estado="ativa").count(),
        "subscricoes_pendentes": subscricoes.filter(estado="pendente").count(),
        "subscricoes_expiradas": subscricoes.filter(estado="expirada").count(),
        "subscricoes_canceladas": subscricoes.filter(estado="cancelada").count(),
    }
