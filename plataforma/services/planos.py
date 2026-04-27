def alternar_plano_ativo(plano):
    plano.ativo = not plano.ativo
    plano.save(update_fields=["ativo"])
    return plano


def criar_plano_via_form(*, form):
    return form.save()


def atualizar_plano_via_form(*, form):
    return form.save()
