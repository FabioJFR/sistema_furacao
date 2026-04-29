from django.db import transaction


@transaction.atomic
def criar_despesa(*, form, empresa):
    despesa = form.save(commit=False)
    despesa.empresa = empresa
    despesa.save()
    return despesa


@transaction.atomic
def apagar_despesa(*, despesa):
    despesa_id = despesa.id
    despesa.delete()
    return despesa_id
