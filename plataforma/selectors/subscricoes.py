from plataforma.models import PagamentoEmpresa, PerfilPlataforma, SubscricaoEmpresa


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


def mapear_pagamentos_pendentes_por_subscricao(subscricoes):
    subscricoes_ids = [str(s.pk) for s in subscricoes]
    if not subscricoes_ids:
        return {}

    pagamentos = (
        PagamentoEmpresa.objects.filter(
            subscricao_id__in=subscricoes_ids,
            estado="pendente",
        )
        .order_by("criado_em")
    )
    mapa = {}
    for pagamento in pagamentos:
        chave = str(pagamento.subscricao_id)
        if chave not in mapa:
            mapa[chave] = pagamento
    return mapa


def mapear_contas_admin_por_empresa(subscricoes):
    empresa_ids = [str(s.empresa_id) for s in subscricoes if getattr(s, "empresa_id", None)]
    if not empresa_ids:
        return {}

    perfis = (
        PerfilPlataforma.objects
        .select_related("user", "empresa")
        .filter(
            empresa_id__in=empresa_ids,
            tipo_acesso="empresa_admin",
        )
        .order_by("criado_em", "user__date_joined")
    )

    mapa = {}
    for perfil in perfis:
        chave = str(perfil.empresa_id)
        if chave not in mapa:
            mapa[chave] = perfil
    return mapa


def obter_metricas_ativacao_contas(subscricoes):
    empresa_ids = [str(s.empresa_id) for s in subscricoes if getattr(s, "empresa_id", None)]
    if not empresa_ids:
        return {
            "contas_admin_ativadas": 0,
            "contas_admin_por_ativar": 0,
        }

    perfis = PerfilPlataforma.objects.filter(
        empresa_id__in=empresa_ids,
        tipo_acesso="empresa_admin",
    )
    return {
        "contas_admin_ativadas": perfis.filter(user__is_active=True).count(),
        "contas_admin_por_ativar": perfis.filter(user__is_active=False).count(),
    }
