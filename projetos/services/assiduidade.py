def criar_assiduidade(*, form, empresa):
    obj = form.save(commit=False)
    obj.empresa = empresa
    obj.save()
    return obj


def atualizar_assiduidade(*, form):
    return form.save()


def apagar_assiduidade(*, obj):
    obj.delete()


def aprovar_assiduidade(*, obj):
    obj.estado = "aprovado"
    obj.save(update_fields=["estado", "atualizado_em"])
    return obj


def rejeitar_assiduidade(*, obj):
    obj.estado = "rejeitado"
    obj.save(update_fields=["estado", "atualizado_em"])
    return obj
