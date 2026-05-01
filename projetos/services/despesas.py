from django.db import transaction
from django.shortcuts import redirect

from projetos.selectors.acesso import obter_perfil_ativo_por_user
from projetos.services.acesso_contexto import obter_empregado_autenticado_contexto


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


def user_tem_conta_individual(*, user):
    perfil = obter_perfil_ativo_por_user(user)
    return bool(perfil and perfil.tipo_acesso == "individual")


def resolver_empregado_individual_para_despesas(*, request):
    if not user_tem_conta_individual(user=request.user):
        return {
            "ok": False,
            "empregado": None,
            "resposta_erro": redirect("projetos:area_empregado"),
            "mensagem_erro": "A área de Despesas está disponível apenas para contas individuais.",
        }

    empregado, _, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
        vincular_por_email=True,
    )
    if resposta_erro:
        return {
            "ok": False,
            "empregado": None,
            "resposta_erro": resposta_erro,
            "mensagem_erro": None,
        }

    return {
        "ok": True,
        "empregado": empregado,
        "resposta_erro": None,
        "mensagem_erro": None,
    }


def processar_submissao_form_despesa(
    *,
    form,
    empresa,
    sucesso_msg,
    erro_msg,
):
    if not form.is_valid():
        return {
            "ok": False,
            "despesa": None,
            "mensagem_sucesso": None,
            "mensagem_erro": erro_msg,
        }

    despesa = criar_despesa(form=form, empresa=empresa)
    return {
        "ok": True,
        "despesa": despesa,
        "mensagem_sucesso": sucesso_msg,
        "mensagem_erro": None,
    }


def processar_submissao_form_despesa_update(
    *,
    form,
    empresa,
    sucesso_msg,
    erro_msg,
):
    if not form.is_valid():
        return {
            "ok": False,
            "despesa": None,
            "mensagem_sucesso": None,
            "mensagem_erro": erro_msg,
        }

    despesa = atualizar_despesa(form=form, empresa=empresa)
    return {
        "ok": True,
        "despesa": despesa,
        "mensagem_sucesso": sucesso_msg,
        "mensagem_erro": None,
    }


@transaction.atomic
def atualizar_despesa(*, form, empresa):
    despesa = form.save(commit=False)
    despesa.empresa = empresa
    despesa.save()
    return despesa


def processar_acao_apagar_despesa(*, despesa):
    despesa_id = apagar_despesa(despesa=despesa)
    return {
        "ok": True,
        "despesa_id": despesa_id,
        "mensagem_sucesso": "Despesa apagada com sucesso.",
    }


def processar_fluxo_form_despesa(
    *,
    method,
    post_data,
    files_data,
    form_class,
    empresa,
    sucesso_msg,
    erro_msg,
    instance=None,
    empregado=None,
    acao="create",
):
    form_kwargs = {"empresa": empresa}
    if instance is not None:
        form_kwargs["instance"] = instance
    if empregado is not None:
        form_kwargs["empregado"] = empregado

    if method == "POST":
        form = form_class(post_data, files_data, **form_kwargs)
        if acao == "update":
            resultado = processar_submissao_form_despesa_update(
                form=form,
                empresa=empresa,
                sucesso_msg=sucesso_msg,
                erro_msg=erro_msg,
            )
        else:
            resultado = processar_submissao_form_despesa(
                form=form,
                empresa=empresa,
                sucesso_msg=sucesso_msg,
                erro_msg=erro_msg,
            )
        return {
            "form": form,
            "resultado": resultado,
        }

    return {
        "form": form_class(**form_kwargs),
        "resultado": None,
    }
