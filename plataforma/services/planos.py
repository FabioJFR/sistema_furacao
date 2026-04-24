def alternar_plano_ativo(plano):
    plano.ativo = not plano.ativo
    plano.save(update_fields=["ativo"])
    return plano
