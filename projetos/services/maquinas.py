from django.core.exceptions import ValidationError
from django.db import transaction

from projetos.models import Maquina, MaquinaTurno


# TODO futuro:
# - centralizar validações multiempresa num helper/base service reutilizável
# - adicionar auditoria de alterações de estado e vínculos da máquina
# - validar regras mais avançadas entre projetos, projeto atual e furos associados

ESTADOS_VALIDOS_MAQUINA = {
    "operacional",
    "avariada",
    "reparacao",
    "parada",
    "sucata",
}


def processar_submissao_form_maquina(
    *,
    form,
    empresa=None,
    acao,
    sucesso_msg,
    erro_msg,
):
    if not form.is_valid():
        return {
            "ok": False,
            "maquina": None,
            "mensagem_sucesso": None,
            "mensagem_erro": erro_msg,
            "erros_form": form.errors,
        }

    if acao == "create":
        maquina = criar_maquina(form=form, empresa=empresa)
    elif acao == "update":
        maquina = atualizar_maquina(form=form, empresa=empresa)
    else:
        raise ValidationError("Ação inválida para submissão de máquina.")

    return {
        "ok": True,
        "maquina": maquina,
        "mensagem_sucesso": sucesso_msg,
        "mensagem_erro": None,
        "erros_form": None,
    }


def processar_fluxo_form_maquina(
    *,
    method,
    post_data,
    form_class,
    empresa,
    acao,
    sucesso_msg,
    erro_msg,
    instance=None,
):
    if method == "POST":
        form = form_class(post_data, instance=instance, empresa=empresa)
        resultado = processar_submissao_form_maquina(
            form=form,
            empresa=empresa,
            acao=acao,
            sucesso_msg=sucesso_msg,
            erro_msg=erro_msg,
        )
        return {
            "form": form,
            "resultado": resultado,
        }

    form = form_class(instance=instance, empresa=empresa)
    return {
        "form": form,
        "resultado": None,
    }



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _atribuir_empresa_maquina(maquina, empresa=None):
    if empresa is None:
        return maquina

    maquina.empresa_id = _resolver_empresa_id(empresa)
    return maquina



def validar_maquina_empresa(maquina, empresa=None):
    if not maquina:
        raise ValidationError("Máquina inválida.")

    if empresa is not None and maquina.empresa_id != _resolver_empresa_id(empresa):
        raise ValidationError("A máquina não pertence à empresa atual.")



def validar_relacoes_maquina_empresa(maquina, empresa=None):
    if empresa is None:
        return

    empresa_id = _resolver_empresa_id(empresa)

    if maquina.projeto_atual and maquina.projeto_atual.empresa_id != empresa_id:
        raise ValidationError({
            "projeto_atual": "O projeto atual não pertence à empresa atual."
        })

    for projeto in maquina.projetos.all():
        if projeto.empresa_id != empresa_id:
            raise ValidationError({
                "projetos": "Um dos projetos associados não pertence à empresa atual."
            })

    for furo in maquina.furos.all():
        if furo.empresa_id != empresa_id:
            raise ValidationError({
                "furos": "Um dos furos associados não pertence à empresa atual."
            })



def _preparar_maquina_para_guardar(maquina, empresa=None):
    _atribuir_empresa_maquina(maquina, empresa=empresa)
    validar_maquina_empresa(maquina, empresa=empresa)
    return maquina



@transaction.atomic
def alterar_estado_maquina(maquina, novo_estado, empresa=None):
    validar_maquina_empresa(maquina, empresa=empresa)

    if novo_estado not in ESTADOS_VALIDOS_MAQUINA:
        raise ValidationError({
            "estado": f"Estado inválido: {novo_estado}."
        })

    maquina.estado = novo_estado
    maquina.save(update_fields=["estado"])

    return maquina



@transaction.atomic
def criar_maquina(form, empresa=None):
    maquina = form.save(commit=False)
    maquina = _preparar_maquina_para_guardar(maquina, empresa=empresa)

    maquina.save()
    form.save_m2m()
    validar_relacoes_maquina_empresa(maquina, empresa=empresa)

    return maquina



@transaction.atomic
def atualizar_maquina(form, empresa=None):
    maquina = form.save(commit=False)
    maquina = _preparar_maquina_para_guardar(maquina, empresa=empresa)

    maquina.save()
    form.save_m2m()
    validar_relacoes_maquina_empresa(maquina, empresa=empresa)

    return maquina


@transaction.atomic
def apagar_maquina(*, maquina, empresa=None):
    validar_maquina_empresa(maquina, empresa=empresa)
    maquina_id = maquina.id
    maquina.delete()
    return maquina_id


@transaction.atomic
def criar_maquina_turno(*, form, maquina, empresa=None):
    validar_maquina_empresa(maquina, empresa=empresa)
    turno = form.save(commit=False)
    turno.maquina = maquina
    turno.save()
    return turno


@transaction.atomic
def atualizar_maquina_turno(*, form, maquina, empresa=None):
    validar_maquina_empresa(maquina, empresa=empresa)
    turno = form.save(commit=False)
    turno.maquina = maquina
    turno.save()
    return turno


@transaction.atomic
def apagar_maquina_turno(*, turno, maquina, empresa=None):
    validar_maquina_empresa(maquina, empresa=empresa)
    if turno.maquina_id != maquina.id:
        raise ValidationError("O turno não pertence à máquina selecionada.")
    turno_id = turno.id
    turno.delete()
    return turno_id


def obter_turno_configurado_maquina(*, maquina=None, turno=None):
    if maquina is None or not turno:
        return None
    return (
        MaquinaTurno.objects.filter(maquina=maquina, turno=turno, ativo=True)
        .order_by("-atualizado_em")
        .first()
    )
