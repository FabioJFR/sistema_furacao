from projetos.models import PedidoCompra


def normalizar_filtros_compras(query_params):
    return {
        "estado": (query_params.get("estado") or "").strip(),
        "prioridade": (query_params.get("prioridade") or "").strip(),
        "projeto_id": (query_params.get("projeto_id") or "").strip(),
        "categoria": (query_params.get("categoria") or "").strip(),
        "q": (query_params.get("q") or "").strip(),
    }


def filtrar_pedidos_compra(*, empresa, filtros):
    queryset = PedidoCompra.objects.filter(empresa=empresa).select_related("projeto", "solicitado_por")

    if filtros.get("estado"):
        queryset = queryset.filter(estado=filtros["estado"])
    if filtros.get("prioridade"):
        queryset = queryset.filter(prioridade=filtros["prioridade"])
    if filtros.get("projeto_id"):
        queryset = queryset.filter(projeto_id=filtros["projeto_id"])
    if filtros.get("categoria"):
        queryset = queryset.filter(categoria__icontains=filtros["categoria"])
    if filtros.get("q"):
        queryset = queryset.filter(descricao__icontains=filtros["q"])

    return queryset.order_by("-criado_em")


def avaliar_propostas_pedido(*, pedido):
    propostas = list(
        pedido.propostas_fornecedor.select_related("fornecedor").order_by(
            "valor_proposto",
            "prazo_entrega_dias",
            "-criado_em",
        )
    )
    if not propostas:
        return []

    valores = [float(proposta.valor_proposto or 0.0) for proposta in propostas]
    prazos = [int(proposta.prazo_entrega_dias or 0) for proposta in propostas]
    min_valor, max_valor = min(valores), max(valores)
    min_prazo, max_prazo = min(prazos), max(prazos)
    range_valor = max(max_valor - min_valor, 1e-9)
    range_prazo = max(max_prazo - min_prazo, 1e-9)

    avaliadas = []
    for proposta in propostas:
        valor = float(proposta.valor_proposto or 0.0)
        prazo = int(proposta.prazo_entrega_dias or 0)
        score_valor = (max_valor - valor) / range_valor
        score_prazo = (max_prazo - prazo) / range_prazo
        score_total = (score_valor * 0.6) + (score_prazo * 0.4)
        avaliadas.append(
            {
                "obj": proposta,
                "score_total": score_total,
            }
        )

    avaliadas.sort(key=lambda item: item["score_total"], reverse=True)
    melhor_id = avaliadas[0]["obj"].id if avaliadas else None
    for item in avaliadas:
        item["is_melhor"] = item["obj"].id == melhor_id
    return avaliadas
