from inspecao_ai.services.box_pipeline import analisar_caixa_cilindrica
from inspecao_ai.services.report_pipeline import analisar_relatorio


def executar_analise_imagem(analise):
    if not analise.imagem_original:
        analise.estado = "erro"
        analise.erro_analise = "A análise não possui imagem original."
        analise.save(update_fields=["estado", "erro_analise", "atualizado_em"])
        return analise

    try:
        if analise.tipo_documento == "relatorio_trabalhador":
            return analisar_relatorio(analise)
        return analisar_caixa_cilindrica(analise)
    except Exception as exc:  # pragma: no cover - fallback defensivo
        analise.estado = "erro"
        analise.erro_analise = str(exc)
        analise.save(update_fields=["estado", "erro_analise", "atualizado_em"])
        return analise
