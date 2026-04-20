def normalizar_leitura(dados):
    return {
        "profundidade": dados.get("depth"),
        "inclinacao": dados.get("inc"),
        "azimute": dados.get("azi"),
        "magnetismo": dados.get("mag"),
    }