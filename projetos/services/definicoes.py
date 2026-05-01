from django.db import transaction


@transaction.atomic
def guardar_preferencias_utilizador(*, form, user, empresa=None):
    preferencias = form.save(commit=False)
    preferencias.user = user
    if empresa is not None:
        preferencias.empresa = empresa
    preferencias.save()
    return preferencias


def processar_submissao_preferencias_utilizador_form(*, form, user, empresa=None):
    if not form.is_valid():
        return {
            "ok": False,
            "preferencias": None,
            "erros_form": form.errors,
        }

    preferencias = guardar_preferencias_utilizador(
        form=form,
        user=user,
        empresa=empresa,
    )
    return {
        "ok": True,
        "preferencias": preferencias,
        "erros_form": None,
    }


def processar_fluxo_preferencias_utilizador_form(
    *,
    method,
    post_data,
    form_class,
    preferencias,
    user,
    empresa=None,
):
    if method == "POST":
        form = form_class(post_data, instance=preferencias)
        resultado = processar_submissao_preferencias_utilizador_form(
            form=form,
            user=user,
            empresa=empresa,
        )
        return {
            "form": form,
            "resultado": resultado,
        }

    return {
        "form": form_class(instance=preferencias),
        "resultado": None,
    }
