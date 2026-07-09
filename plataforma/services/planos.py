from django.utils.translation import gettext as _

from plataforma.forms.plano import PlanoForm
from plataforma.selectors.planos import (
    enriquecer_planos_com_contexto_trial,
    listar_planos_dashboard,
    plano_e_trial,
)


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


def construir_contexto_plano_list():
    planos = listar_planos_dashboard()
    enriquecer_planos_com_contexto_trial(planos)
    return {
        "planos": planos,
        "planos_ativos": planos.filter(ativo=True).count(),
        "planos_empresa": planos.filter(tipo="empresa").count(),
        "planos_individuais": planos.filter(tipo="individual").count(),
        "planos_trial": sum(1 for plano in planos if plano_e_trial(plano)),
    }


def construir_contexto_form_plano(*, form, titulo, plano=None):
    context = {
        "form": form,
        "titulo": titulo,
    }
    if plano is not None:
        context["plano"] = plano
    return context


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


def processar_fluxo_form_plano(*, method, post_data, plano=None):
    if method == "POST":
        if plano is None:
            resultado = processar_submissao_plano_create(post_data=post_data)
        else:
            resultado = processar_submissao_plano_update(post_data=post_data, plano=plano)
        return {
            "form": resultado["form"],
            "resultado": resultado,
        }

    return {
        "form": construir_form_plano(instance=plano),
        "resultado": None,
    }
