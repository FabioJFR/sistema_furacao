from django.core.exceptions import ValidationError
from django.db import transaction


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


@transaction.atomic
def atualizar_dados_individual(*, form, user):
    individual = form.save(commit=False)
    individual.user = user
    individual.save()
    form.save_m2m()
    return individual


@transaction.atomic
def atualizar_dados_empregado(*, form, user, empresa=None):
    empregado = form.save(commit=False)
    empregado.user = user

    if empresa is not None:
        empresa_id = _resolver_empresa_id(empresa)
        if empregado.empresa_id and empregado.empresa_id != empresa_id:
            raise ValidationError("O empregado não pertence à empresa atual.")
        empregado.empresa_id = empresa_id

    empregado.save()
    form.save_m2m()
    return empregado
