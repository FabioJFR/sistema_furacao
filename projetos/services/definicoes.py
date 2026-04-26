from django.db import transaction


@transaction.atomic
def guardar_preferencias_utilizador(*, form, user, empresa=None):
    preferencias = form.save(commit=False)
    preferencias.user = user
    if empresa is not None:
        preferencias.empresa = empresa
    preferencias.save()
    return preferencias
