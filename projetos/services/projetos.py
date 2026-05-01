from django.core.exceptions import ValidationError
from django.db import transaction

from core.utils.coordenadas import obter_coordenadas_por_cidade_pais
from projetos.models import EmpregadoProjeto, Projeto


# ==============================
# HELPERS
# ==============================


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _atribuir_empresa_projeto(projeto, empresa=None):
    if empresa is None:
        return projeto

    projeto.empresa_id = _resolver_empresa_id(empresa)
    return projeto



def preparar_localizacao_projeto(projeto):
    """
    Preenche latitude e longitude com base em cidade e país.
    """
    if projeto.cidade and projeto.pais:
        lat, lon = obter_coordenadas_por_cidade_pais(
            projeto.cidade,
            projeto.pais,
        )
        projeto.localizacao_lat = lat
        projeto.localizacao_lon = lon

    return projeto



def _validar_projeto_empresa(projeto, empresa=None):
    if empresa is None:
        return

    empresa_id = _resolver_empresa_id(empresa)
    if projeto.empresa_id and projeto.empresa_id != empresa_id:
        raise ValidationError("O projeto não pertence à empresa atual.")



def _preparar_projeto_para_guardar(projeto, empresa=None):
    _atribuir_empresa_projeto(projeto, empresa=empresa)
    _validar_projeto_empresa(projeto, empresa=empresa)
    preparar_localizacao_projeto(projeto)
    return projeto


# ==============================
# SERVICES
# ==============================


def criar_projeto(form, empresa=None):
    projeto = form.save(commit=False)
    projeto = _preparar_projeto_para_guardar(projeto, empresa=empresa)

    projeto.save()
    form.save_m2m()

    return projeto



def atualizar_projeto(form, empresa=None):
    projeto = form.save(commit=False)
    projeto = _preparar_projeto_para_guardar(projeto, empresa=empresa)

    projeto.save()
    form.save_m2m()

    return projeto


def processar_submissao_form_projeto(
    *,
    form,
    empresa=None,
    on_success,
    sucesso_msg,
    erro_msg,
):
    if not form.is_valid():
        return {
            "ok": False,
            "projeto": None,
            "mensagem_sucesso": None,
            "mensagem_erro": erro_msg,
            "erros": form.errors,
        }

    projeto = on_success(form=form, empresa=_resolver_empresa_id(empresa))
    return {
        "ok": True,
        "projeto": projeto,
        "mensagem_sucesso": sucesso_msg,
        "mensagem_erro": None,
        "erros": None,
    }


def associar_empregado_projeto(*, empregado, projeto, empresa=None, data_inicio=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else projeto.empresa_id

    if empregado.empresa_id != empresa_id:
        raise ValidationError("O empregado não pertence à empresa atual.")
    if projeto.empresa_id != empresa_id:
        raise ValidationError("O projeto não pertence à empresa atual.")

    ligacao = EmpregadoProjeto.objects.filter(
        empregado=empregado,
        projeto=projeto,
        empresa_id=empresa_id,
        ativo=True,
    ).first()
    if ligacao:
        return ligacao, False

    ligacao = EmpregadoProjeto.objects.create(
        empregado=empregado,
        projeto=projeto,
        empresa_id=empresa_id,
        data_inicio=data_inicio,
        ativo=True,
    )
    return ligacao, True


def processar_acao_associar_empregado_projeto(
    *,
    form,
    projeto,
    empresa=None,
):
    if not form.is_valid():
        return {
            "ok": False,
            "mensagem_sucesso": None,
            "mensagem_erro": "Erro ao associar empregado ao projeto. Verifique os dados.",
            "mensagem_aviso": None,
            "ligacao": None,
            "criado": False,
            "erros": form.errors,
        }

    empregado = form.cleaned_data["empregado"]
    ligacao, criado = associar_empregado_projeto(
        empregado=empregado,
        projeto=projeto,
        empresa=empresa,
        data_inicio=form.cleaned_data.get("data_inicio"),
    )
    if not criado:
        return {
            "ok": True,
            "mensagem_sucesso": None,
            "mensagem_erro": None,
            "mensagem_aviso": "Este empregado já está associado a este projeto.",
            "ligacao": ligacao,
            "criado": False,
            "erros": None,
        }

    return {
        "ok": True,
        "mensagem_sucesso": "Empregado associado ao projeto com sucesso.",
        "mensagem_erro": None,
        "mensagem_aviso": None,
        "ligacao": ligacao,
        "criado": True,
        "erros": None,
    }


@transaction.atomic
def apagar_projeto(*, projeto, empresa=None):
    _validar_projeto_empresa(projeto, empresa=empresa)
    projeto_id = projeto.pk
    projeto.delete()
    return projeto_id
