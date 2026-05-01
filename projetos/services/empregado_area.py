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


def processar_submissao_meus_dados_individual_form(*, form, user):
    if not form.is_valid():
        return {
            "ok": False,
            "individual": None,
            "erro": "form_invalido",
            "erros_form": form.errors,
        }

    individual = atualizar_dados_individual(
        form=form,
        user=user,
    )
    return {
        "ok": True,
        "individual": individual,
        "erro": None,
        "erros_form": None,
    }


def processar_submissao_meus_dados_empregado_form(*, form, user, empresa):
    if not form.is_valid():
        return {
            "ok": False,
            "empregado": None,
            "erro": "form_invalido",
            "erros_form": form.errors,
        }

    try:
        empregado = atualizar_dados_empregado(
            form=form,
            user=user,
            empresa=empresa,
        )
        return {
            "ok": True,
            "empregado": empregado,
            "erro": None,
            "erros_form": None,
        }
    except ValidationError:
        return {
            "ok": False,
            "empregado": None,
            "erro": "validacao",
            "erros_form": form.errors,
        }


def processar_fluxo_meus_dados_individual_form(
    *,
    method,
    post_data,
    files_data,
    form_class,
    instance,
    user,
):
    if method == "POST":
        form = form_class(post_data, files_data, instance=instance)
        resultado = processar_submissao_meus_dados_individual_form(
            form=form,
            user=user,
        )
        return {
            "form": form,
            "resultado": resultado,
        }

    return {
        "form": form_class(instance=instance),
        "resultado": None,
    }


def processar_fluxo_meus_dados_empregado_form(
    *,
    method,
    post_data,
    files_data,
    form_class,
    instance,
    user,
    empresa,
):
    if method == "POST":
        form = form_class(post_data, files_data, instance=instance)
        resultado = processar_submissao_meus_dados_empregado_form(
            form=form,
            user=user,
            empresa=empresa,
        )
        return {
            "form": form,
            "resultado": resultado,
        }

    return {
        "form": form_class(instance=instance),
        "resultado": None,
    }
