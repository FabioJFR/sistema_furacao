from django.core.exceptions import ValidationError
from django.db import transaction

from projetos.models import HistoricoConfiguracaoPerfuracao


@transaction.atomic
def guardar_configuracao_perfuracao(
    *,
    form,
    empregado,
    empresa,
    atualizado_por,
    acao_historico,
    observacoes_historico,
):
    configuracao = form.save(commit=False)
    configuracao.empregado = empregado
    configuracao.empresa = empresa
    configuracao.atualizado_por = atualizado_por
    configuracao.save()

    HistoricoConfiguracaoPerfuracao.registar_historico(
        configuracao=configuracao,
        acao=acao_historico,
        utilizador=atualizado_por,
        observacoes=observacoes_historico,
    )
    return configuracao


@transaction.atomic
def apagar_configuracao_perfuracao(*, configuracao, utilizador, observacoes_historico):
    HistoricoConfiguracaoPerfuracao.registar_historico(
        configuracao=configuracao,
        acao="apagado",
        utilizador=utilizador,
        observacoes=observacoes_historico,
    )
    configuracao_id = configuracao.id
    configuracao.delete()
    return configuracao_id


def _aplicar_validation_error_no_form(form, erro):
    if hasattr(erro, "message_dict"):
        for campo, erros in erro.message_dict.items():
            for item in erros:
                form.add_error(campo, item)
        return
    form.add_error(None, erro)


def preparar_form_configuracao_perfuracao(
    *,
    form_class,
    request_method,
    post_data,
    empregado,
    empresa,
    atualizado_por,
    instance=None,
    initial=None,
):
    form = form_class(
        post_data if request_method == "POST" else None,
        instance=instance,
        initial=initial if request_method != "POST" else None,
        empregado=empregado,
    )
    form.instance.empregado = empregado
    form.instance.empresa = empresa
    form.instance.atualizado_por = atualizado_por
    return form


def processar_fluxo_form_configuracao_perfuracao(
    *,
    request_method,
    post_data,
    form_class,
    empregado,
    empresa,
    atualizado_por,
    instance=None,
    initial=None,
    acao_historico,
    observacoes_historico,
):
    form = preparar_form_configuracao_perfuracao(
        form_class=form_class,
        request_method=request_method,
        post_data=post_data,
        empregado=empregado,
        empresa=empresa,
        atualizado_por=atualizado_por,
        instance=instance,
        initial=initial,
    )
    if request_method != "POST":
        return {
            "form": form,
            "resultado": None,
        }

    if not form.is_valid():
        return {
            "form": form,
            "resultado": {
                "ok": False,
                "configuracao": None,
                "erros_form": form.errors,
            },
        }

    try:
        configuracao = guardar_configuracao_perfuracao(
            form=form,
            empregado=empregado,
            empresa=empresa,
            atualizado_por=atualizado_por,
            acao_historico=acao_historico,
            observacoes_historico=observacoes_historico,
        )
        return {
            "form": form,
            "resultado": {
                "ok": True,
                "configuracao": configuracao,
                "erros_form": None,
            },
        }
    except ValidationError as erro:
        _aplicar_validation_error_no_form(form, erro)
        return {
            "form": form,
            "resultado": {
                "ok": False,
                "configuracao": None,
                "erros_form": form.errors,
            },
        }
