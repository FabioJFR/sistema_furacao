def _filtrar_por_leitura(documentos, filtro_leitura):
    if filtro_leitura == "direta":
        return [item for item in documentos if item["leitura"] == "direta"]
    if filtro_leitura == "txt_auxiliar":
        return [item for item in documentos if item["leitura"] == "txt_auxiliar"]
    if filtro_leitura == "nao_preparado":
        return [item for item in documentos if item["leitura"] == "nao_preparado"]
    return list(documentos)


def _filtrar_por_extensao(documentos, filtro_extensao):
    if filtro_extensao == "todas":
        return list(documentos)
    return [item for item in documentos if item["extensao"] == filtro_extensao]


def construir_contexto_biblioteca(*, documentos, filtro_leitura="todas", filtro_extensao="todas"):
    documentos_filtrados = _filtrar_por_leitura(documentos, filtro_leitura)
    documentos_filtrados = _filtrar_por_extensao(documentos_filtrados, filtro_extensao)

    extensoes_disponiveis = sorted(
        {
            item["extensao"]
            for item in documentos
            if item["extensao"] and item["extensao"] != "(sem extensão)"
        }
    )

    return {
        "documentos": documentos_filtrados,
        "filtro_leitura": filtro_leitura,
        "filtro_extensao": filtro_extensao,
        "extensoes_disponiveis": extensoes_disponiveis,
        "filtro_choices": [
            ("todas", "Todos"),
            ("direta", "Leitura direta"),
            ("txt_auxiliar", "TXT auxiliar"),
            ("nao_preparado", "Não preparado"),
        ],
        "extensao_choices": [("todas", "Todas")] + [(item, item) for item in extensoes_disponiveis],
        "total_pdfs": sum(1 for item in documentos_filtrados if item["extensao"] == ".pdf"),
        "total_pdfs_com_txt": sum(
            1 for item in documentos_filtrados if item["extensao"] == ".pdf" and item["tem_txt"]
        ),
        "total_pdfs_sem_txt": sum(
            1 for item in documentos_filtrados if item["extensao"] == ".pdf" and not item["tem_txt"]
        ),
        "total_documentos": len(documentos_filtrados),
        "total_leitura_direta": sum(1 for item in documentos_filtrados if item["leitura"] == "direta"),
        "total_txt_auxiliar": sum(1 for item in documentos_filtrados if item["leitura"] == "txt_auxiliar"),
        "total_nao_preparado": sum(1 for item in documentos_filtrados if item["leitura"] == "nao_preparado"),
    }
