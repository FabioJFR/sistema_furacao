from projetos.models import BlockModelCell, Modelo3DBlock


def obter_block_models_projeto(projeto):
    qs = Modelo3DBlock.objects.select_related("empresa", "projeto", "criado_por")
    if projeto is None:
        return qs.none()
    return qs.filter(projeto=projeto).order_by("-criado_em")


def obter_celulas_block_model(block_model):
    if block_model is None:
        return BlockModelCell.objects.none()
    return BlockModelCell.objects.filter(block_model=block_model).order_by("x", "y", "z")


def obter_dados_3d_block_model(block_model):
    celulas = obter_celulas_block_model(block_model)
    dados = []
    for c in celulas:
        dados.append(
            {
                "x": c.x,
                "y": c.y,
                "z": c.z,
                "centro_x": c.centro_x,
                "centro_y": c.centro_y,
                "centro_z": c.centro_z,
                "litologia": c.litologia or "default",
                "dureza_media": c.dureza_media,
                "densidade": c.densidade,
                "teor": c.teor,
                "distancia_ao_furo": c.distancia_ao_furo,
                "dados_json": c.dados_json or {},
            }
        )
    return dados
