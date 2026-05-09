def _intervalo_sobrepoe(a_inicio, a_fim, b_inicio, b_fim):
    return a_inicio <= b_fim and b_inicio <= a_fim


def detetar_conflitos_planeamento(*, items, max_resultados=30):
    """
    Deteta sobreposição de planeamentos no mesmo recurso (empregado/máquina).
    Considera apenas estados operacionais: planeado/confirmado.
    """
    ativos = [i for i in items if i.estado in {"planeado", "confirmado"}]

    conflitos = []
    vistos = set()

    def processar_grupo(grupo_items, tipo):
        grupo = sorted(grupo_items, key=lambda x: (x.data_inicio, x.data_fim or x.data_inicio, str(x.id)))
        for idx, atual in enumerate(grupo):
            atual_inicio = atual.inicio_datetime
            atual_fim = atual.fim_datetime
            for prox in grupo[idx + 1 :]:
                prox_inicio = prox.inicio_datetime
                prox_fim = prox.fim_datetime

                if prox_inicio > atual_fim:
                    break
                if not _intervalo_sobrepoe(atual_inicio, atual_fim, prox_inicio, prox_fim):
                    continue

                chave = tuple(sorted([str(atual.id), str(prox.id)]))
                if chave in vistos:
                    continue
                vistos.add(chave)

                conflito_inicio = max(atual_inicio, prox_inicio)
                conflito_fim = min(atual_fim, prox_fim)

                conflitos.append(
                    {
                        "recurso_tipo": tipo,
                        "recurso_nome": (
                            atual.empregado.nome if tipo == "empregado" and atual.empregado else
                            atual.maquina.nome if tipo == "maquina" and atual.maquina else
                            "-"
                        ),
                        "inicio": conflito_inicio,
                        "fim": conflito_fim,
                        "a": atual,
                        "b": prox,
                    }
                )
                if len(conflitos) >= max_resultados:
                    return

    grupos_empregado = {}
    grupos_maquina = {}
    for item in ativos:
        if item.empregado_id:
            grupos_empregado.setdefault(item.empregado_id, []).append(item)
        if item.maquina_id:
            grupos_maquina.setdefault(item.maquina_id, []).append(item)

    for grupo in grupos_empregado.values():
        processar_grupo(grupo, "empregado")
        if len(conflitos) >= max_resultados:
            return conflitos

    for grupo in grupos_maquina.values():
        processar_grupo(grupo, "maquina")
        if len(conflitos) >= max_resultados:
            return conflitos

    return conflitos


def escolher_planeamento_cancelar_automatico(*, item_a, item_b):
    """
    Regra de desempate para resolução automática:
    1) Cancela o de menor prioridade.
    2) Em empate, cancela o que está em `planeado` (preserva o `confirmado`).
    3) Em novo empate, cancela o mais recentemente atualizado.
    """
    prioridade_a = int(item_a.prioridade or 0)
    prioridade_b = int(item_b.prioridade or 0)
    if prioridade_a != prioridade_b:
        return (item_a, f"prioridade menor ({prioridade_a} < {prioridade_b})") if prioridade_a < prioridade_b else (item_b, f"prioridade menor ({prioridade_b} < {prioridade_a})")

    if item_a.estado != item_b.estado:
        if item_a.estado == "planeado":
            return item_a, "estado planeado (preferência por manter confirmado)"
        if item_b.estado == "planeado":
            return item_b, "estado planeado (preferência por manter confirmado)"

    if item_a.atualizado_em >= item_b.atualizado_em:
        return item_a, "atualização mais recente"
    return item_b, "atualização mais recente"
