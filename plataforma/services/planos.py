from django.utils.translation import gettext as _

from plataforma.forms.plano import PlanoForm


def alternar_plano_ativo(plano):
    plano.ativo = not plano.ativo
    plano.save(update_fields=["ativo"])
    return plano


def criar_plano_via_form(*, form):
    return form.save()


def atualizar_plano_via_form(*, form):
    return form.save()


def construir_form_plano(*, post_data=None, instance=None):
    if post_data is not None:
        return PlanoForm(post_data, instance=instance)
    return PlanoForm(instance=instance)


def processar_submissao_plano_create(*, post_data):
    form = construir_form_plano(post_data=post_data)
    if not form.is_valid():
        return {
            "ok": False,
            "form": form,
            "mensagem": _("Erro ao criar plano. Verifique os dados."),
            "plano": None,
        }
    plano = criar_plano_via_form(form=form)
    return {
        "ok": True,
        "form": form,
        "mensagem": _("Plano '%(nome)s' criado com sucesso.") % {"nome": plano.nome},
        "plano": plano,
    }


def processar_submissao_plano_update(*, post_data, plano):
    form = construir_form_plano(post_data=post_data, instance=plano)
    if not form.is_valid():
        return {
            "ok": False,
            "form": form,
            "mensagem": _("Erro ao atualizar plano."),
            "plano": plano,
        }
    plano_atualizado = atualizar_plano_via_form(form=form)
    return {
        "ok": True,
        "form": form,
        "mensagem": _("Plano atualizado com sucesso."),
        "plano": plano_atualizado,
    }
