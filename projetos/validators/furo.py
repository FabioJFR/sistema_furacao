CAMPOS_INCLINACAO_FURO = [
    "inclinacao_planeada_inicial",
    "inclinacao_planeada_atual",
    "inclinacao_real_atual",
]

MENSAGEM_INCLINACAO_SUPERFICIE_POSITIVA = "Para furos de Superfície, a inclinação não pode ser positiva."


def validar_inclinacoes_por_tipo_furo(*, tipo, valores):
    tipo_normalizado = (tipo or "").strip().lower()
    if tipo_normalizado != "superficie":
        return {}

    erros = {}
    for campo in CAMPOS_INCLINACAO_FURO:
        valor = valores.get(campo)
        if valor is not None and valor > 0:
            erros[campo] = MENSAGEM_INCLINACAO_SUPERFICIE_POSITIVA
    return erros
