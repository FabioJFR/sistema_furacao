from django.db import transaction

from inspecao_ai.domain_logic import normalizar_valor_comparacao_ai
from inspecao_ai.models import ExemploTreinoAI


def construir_entrada_modelo(*, analise, campo, indice_campo):
    return {
        "analise_id": str(analise.pk),
        "tipo_documento": analise.tipo_documento,
        "motor_analise": analise.motor_analise,
        "indice_campo": indice_campo,
        "campo": campo.get("campo") or "",
        "campo_impresso": campo.get("campo_impresso") or "",
        "campo_semantico": campo.get("campo_semantico") or "campo_livre",
        "tipo_conteudo": campo.get("tipo_conteudo") or "",
        "valor_previsto": campo.get("valor_lido") or "",
        "confianca": campo.get("confianca"),
        "ocr_aceite": bool(campo.get("ocr_aceite")),
    }


@transaction.atomic
def sincronizar_exemplos_validacao(*, analise, campos, utilizador=None):
    criados = []
    for indice, campo in enumerate(campos):
        rotulo = (campo.get("valor_validado") or "").strip()
        if not campo.get("validado_utilizador") or not rotulo:
            continue

        campo_semantico = campo.get("campo_semantico") or campo.get("campo") or "campo_livre"
        entrada_modelo = construir_entrada_modelo(analise=analise, campo=campo, indice_campo=indice)
        atual = (
            ExemploTreinoAI.objects.filter(analise=analise, indice_campo=indice, ativo=True)
            .order_by("-versao_rotulo")
            .first()
        )
        if atual and atual.rotulo_validado == rotulo and atual.entrada_modelo == entrada_modelo:
            continue

        ultima = (
            ExemploTreinoAI.objects.filter(analise=analise, indice_campo=indice)
            .order_by("-versao_rotulo")
            .first()
        )
        if atual:
            atual.ativo = False
            atual.save(update_fields=["ativo"])

        valor_previsto = campo.get("valor_lido") or ""
        exemplo = ExemploTreinoAI.objects.create(
            empresa=analise.empresa,
            analise=analise,
            validado_por=utilizador,
            tipo_documento=analise.tipo_documento,
            campo_semantico=campo_semantico,
            indice_campo=indice,
            versao_rotulo=(ultima.versao_rotulo + 1) if ultima else 1,
            entrada_modelo=entrada_modelo,
            valor_previsto=valor_previsto,
            rotulo_validado=rotulo,
            acertou_previsao=(
                normalizar_valor_comparacao_ai(valor_previsto) == normalizar_valor_comparacao_ai(rotulo)
            ),
            motor_analise=analise.motor_analise,
        )
        criados.append(exemplo)

    return criados
