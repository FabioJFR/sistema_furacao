from inspecao_ai.models import ExemploTreinoAI


def listar_exemplos_treino_empresa(empresa):
    return list(
        ExemploTreinoAI.objects.filter(empresa=empresa)
        .select_related("analise")
        .values(
            "analise_id",
            "analise__nome",
            "tipo_documento",
            "campo_semantico",
            "indice_campo",
            "versao_rotulo",
            "ativo",
            "rotulo_validado",
            "valor_previsto",
            "acertou_previsao",
            "motor_analise",
            "criado_em",
        )
        .order_by("-criado_em")
    )
