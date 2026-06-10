from collections import defaultdict

from inspecao_ai.domain_logic import normalizar_valor_comparacao_ai


MIN_EXEMPLOS_BASELINE = 30
MIN_EXEMPLOS_VALIDACAO = 10
DOCUMENTO_LABELS = {
    "caixa_cilindrica": "Caixa cilíndrica",
    "relatorio_trabalhador": "Relatório manuscrito",
}


def construir_contexto_qualidade_dataset(exemplos):
    exemplos = list(exemplos or [])
    ativos = [item for item in exemplos if item.get("ativo")]
    agrupados_campos = _contar_por_chave(ativos, "campo_semantico")
    revisoes = _listar_revisoes_rotulo(exemplos)
    conflitos = _listar_conflitos_ativos(ativos)
    total_acertos = sum(1 for item in ativos if item.get("acertou_previsao") is True)
    total_avaliaveis = sum(1 for item in ativos if item.get("acertou_previsao") is not None)
    melhor_campo = agrupados_campos[0] if agrupados_campos else None

    total_ativos = len(ativos)
    treino, validacao, teste = _sugerir_split(total_ativos)
    cobertura_documentos = [
        {
            "key": chave,
            "label": DOCUMENTO_LABELS[chave],
            "total": sum(1 for item in ativos if item.get("tipo_documento") == chave),
        }
        for chave in DOCUMENTO_LABELS
    ]
    documentos_sem_exemplos = [item["label"] for item in cobertura_documentos if item["total"] == 0]

    pronto_volume = bool(melhor_campo and melhor_campo["total"] >= MIN_EXEMPLOS_BASELINE)
    pronto_validacao = total_ativos >= MIN_EXEMPLOS_VALIDACAO
    pronto_sem_conflitos = not conflitos
    pronto_baseline = pronto_volume and pronto_validacao and pronto_sem_conflitos

    return {
        "total_ativos": total_ativos,
        "total_versoes": len(exemplos),
        "total_analises": len({str(item.get("analise_id")) for item in ativos}),
        "total_revisoes": len(revisoes),
        "total_conflitos": len(conflitos),
        "taxa_acerto_atual": round((total_acertos / total_avaliaveis) * 100, 1) if total_avaliaveis else None,
        "por_campo": agrupados_campos[:8],
        "por_documento": cobertura_documentos,
        "documentos_sem_exemplos": documentos_sem_exemplos,
        "revisoes": revisoes[:8],
        "conflitos": conflitos[:8],
        "split_sugerido": {"treino": treino, "validacao": validacao, "teste": teste},
        "min_exemplos_baseline": MIN_EXEMPLOS_BASELINE,
        "melhor_campo": melhor_campo,
        "pronto_baseline": pronto_baseline,
        "checks_prontidao": [
            {
                "label": f"Campo prioritário com {MIN_EXEMPLOS_BASELINE}+ exemplos",
                "ok": pronto_volume,
            },
            {
                "label": f"Dataset com {MIN_EXEMPLOS_VALIDACAO}+ exemplos ativos",
                "ok": pronto_validacao,
            },
            {
                "label": "Sem conflitos de rótulo por resolver",
                "ok": pronto_sem_conflitos,
            },
        ],
    }


def _contar_por_chave(exemplos, chave):
    totais = defaultdict(int)
    for item in exemplos:
        valor = item.get(chave) or "campo_livre"
        totais[valor] += 1
    return [
        {"key": valor, "label": valor.replace("_", " "), "total": total}
        for valor, total in sorted(totais.items(), key=lambda entry: (-entry[1], entry[0]))
    ]


def _listar_revisoes_rotulo(exemplos):
    grupos = defaultdict(list)
    for item in exemplos:
        key = (str(item.get("analise_id")), item.get("indice_campo"))
        grupos[key].append(item)

    revisoes = []
    for itens in grupos.values():
        rotulos = {
            normalizar_valor_comparacao_ai(item.get("rotulo_validado"))
            for item in itens
            if item.get("rotulo_validado")
        }
        if len(rotulos) <= 1:
            continue
        atual = next((item for item in itens if item.get("ativo")), itens[0])
        revisoes.append(
            {
                "analise_nome": atual.get("analise__nome") or "Análise",
                "campo": (atual.get("campo_semantico") or "campo_livre").replace("_", " "),
                "versoes": len(itens),
                "rotulos_distintos": len(rotulos),
            }
        )
    return sorted(revisoes, key=lambda item: (-item["rotulos_distintos"], item["campo"], item["analise_nome"]))


def _listar_conflitos_ativos(exemplos):
    grupos = defaultdict(list)
    for item in exemplos:
        key = (str(item.get("analise_id")), item.get("indice_campo"))
        grupos[key].append(item)

    conflitos = []
    for itens in grupos.values():
        rotulos = {
            normalizar_valor_comparacao_ai(item.get("rotulo_validado"))
            for item in itens
            if item.get("rotulo_validado")
        }
        if len(rotulos) <= 1:
            continue
        atual = itens[0]
        conflitos.append(
            {
                "analise_nome": atual.get("analise__nome") or "Análise",
                "campo": (atual.get("campo_semantico") or "campo_livre").replace("_", " "),
                "versoes": len(itens),
                "rotulos_distintos": len(rotulos),
            }
        )
    return sorted(conflitos, key=lambda item: (-item["rotulos_distintos"], item["campo"], item["analise_nome"]))


def _sugerir_split(total):
    if not total:
        return 0, 0, 0
    treino = max(1, round(total * 0.7))
    validacao = round(total * 0.15)
    teste = total - treino - validacao
    if total >= 3 and validacao == 0:
        validacao = 1
        treino -= 1
    if total >= 3 and teste == 0:
        teste = 1
        treino -= 1
    return treino, validacao, teste
