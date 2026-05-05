def criar_cliente_contrato(*, form, empresa):
    obj = form.save(commit=False)
    obj.empresa = empresa
    obj.save()
    return obj


def atualizar_cliente_contrato(*, form):
    return form.save()


def apagar_cliente_contrato(*, cliente_contrato):
    cliente_contrato.delete()
