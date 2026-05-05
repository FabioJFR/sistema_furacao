def criar_planeamento_turno(*, form, empresa):
    obj = form.save(commit=False)
    obj.empresa = empresa
    obj.save()
    return obj


def atualizar_planeamento_turno(*, form):
    return form.save()


def apagar_planeamento_turno(*, obj):
    obj.delete()
