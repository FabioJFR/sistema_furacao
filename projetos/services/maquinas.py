from django.core.exceptions import ValidationError
from django.db import transaction

from projetos.models import Maquina


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