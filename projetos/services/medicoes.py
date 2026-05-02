from django.core.exceptions import ValidationError
from django.db import transaction

from projetos.models import Medicao
from projetos.services.furo_versioning import registar_versao_furo


# TODO futuro:
# - adicionar auditoria de criação/edição/apagamento de medições
# - centralizar snapshots técnicos num helper reutilizável
# - emitir eventos para dashboard/3D em tempo real, se necessário



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _atribuir_empresa_medicao(medicao, empresa=None):
    if empresa is None:
        return medicao

    medicao.empresa_id = _resolver_empresa_id(empresa)
    return medicao



def validar_medicao_empresa_existente(medicao, empresa=None):
    if (
        empresa is not None
        and medicao.pk
        and medicao.empresa_id
        and medicao.empresa_id != _resolver_empresa_id(empresa)
    ):
        raise ValidationError("A medição não pertence à empresa atual.")



def atualizar_estado_real_furo_por_medicao(furo, medicao_referencia=None):
    """
    Atualiza apenas os campos reais/orientacionais do furo com base na medição.
    A profundidade atual e a profundidade máxima continuam a ser controladas
    pelos registos de produção, não pelas medições.
    """
    if medicao_referencia is None:
        return furo

    if medicao_referencia.inclinacao_real_medida is not None:
        furo.inclinacao_real_atual = medicao_referencia.inclinacao_real_medida

    if medicao_referencia.azimute_real_medido is not None:
        furo.azimute_real_atual = medicao_referencia.azimute_real_medido

    if medicao_referencia.magnetismo is not None:
        furo.magnetismo = medicao_referencia.magnetismo

    furo.save(update_fields=[
        "inclinacao_real_atual",
        "azimute_real_atual",
        "magnetismo",
    ])

    return furo



def preparar_snapshot_medicao(medicao, furo):
    medicao.furo = furo
    medicao.nome_furo_snapshot = furo.nome

    # Herdar localização do furo se a medição não trouxer
    if medicao.latitude is None:
        medicao.latitude = furo.latitude
    if medicao.longitude is None:
        medicao.longitude = furo.longitude
    if medicao.altitude is None:
        medicao.altitude = furo.altitude

    # Snapshot do planeamento do furo no momento da medição
    medicao.profundidade_alvo_inicial_furo = furo.profundidade_alvo_inicial
    medicao.profundidade_alvo_atual_furo = furo.profundidade_alvo_atual

    medicao.inclinacao_planeada_inicial_furo = furo.inclinacao_planeada_inicial
    medicao.inclinacao_planeada_atual_furo = furo.inclinacao_planeada_atual

    medicao.azimute_planeado_inicial_furo = furo.azimute_planeado_inicial
    medicao.azimute_planeado_atual_furo = furo.azimute_planeado_atual

    return medicao



def validar_medicao_no_furo(medicao, furo, empresa=None):
    if not furo:
        raise ValidationError("A medição tem de estar associada a um furo.")

    validar_medicao_empresa_existente(medicao, empresa=empresa)

    if empresa is not None:
        empresa_id = _resolver_empresa_id(empresa)

        if not furo.empresa_id or furo.empresa_id != empresa_id:
            raise ValidationError("O furo da medição não pertence à empresa atual.")

        if medicao.empresa_id and medicao.empresa_id != empresa_id:
            raise ValidationError("A medição não pertence à empresa atual.")

    if medicao.profundidade_medida is not None:
        profundidade_atual_furo = float(furo.profundidade_atual or 0.0)
        profundidade_medida = float(medicao.profundidade_medida or 0.0)

        if profundidade_medida > profundidade_atual_furo:
            raise ValidationError(
                f"Não é possível registar uma medição aos {profundidade_medida:.2f} m porque o furo tem atualmente {profundidade_atual_furo:.2f} m."
            )

    return medicao



def _preparar_medicao_para_guardar(medicao, empresa=None, furo=None):
    validar_medicao_empresa_existente(medicao, empresa=empresa)
    _atribuir_empresa_medicao(medicao, empresa=empresa)

    furo_relacionado = furo or medicao.furo
    if furo_relacionado is None:
        return medicao

    validar_medicao_no_furo(medicao, furo_relacionado, empresa=empresa)
    preparar_snapshot_medicao(medicao, furo_relacionado)
    return medicao



@transaction.atomic
def criar_medicao(form, furo=None, empresa=None):
    medicao = form.save(commit=False)
    medicao = _preparar_medicao_para_guardar(medicao, empresa=empresa, furo=furo)

    medicao.save()

    if medicao.furo:
        atualizar_estado_real_furo_por_medicao(medicao.furo, medicao)
        registar_versao_furo(medicao.furo, origem="medicao")

    return medicao



@transaction.atomic
def atualizar_medicao(form, empresa=None):
    medicao = form.save(commit=False)
    medicao = _preparar_medicao_para_guardar(medicao, empresa=empresa)

    medicao.save()

    if medicao.furo:
        atualizar_estado_real_furo_por_medicao(medicao.furo, medicao)
        registar_versao_furo(medicao.furo, origem="medicao")

    return medicao


@transaction.atomic
def apagar_medicao(*, medicao, empresa=None):
    validar_medicao_empresa_existente(medicao, empresa=empresa)
    medicao_id = medicao.pk
    medicao.delete()
    return medicao_id


def processar_submissao_form_medicao(
    *,
    form,
    empresa,
    furo,
    sucesso_msg,
    erro_msg,
):
    if not form.is_valid():
        return {
            "ok": False,
            "medicao": None,
            "erro": None,
            "mensagem_sucesso": None,
            "mensagem_erro": erro_msg,
        }

    try:
        medicao = criar_medicao(form, furo=furo, empresa=empresa)
    except ValidationError as erro:
        form.add_error(None, erro)
        return {
            "ok": False,
            "medicao": None,
            "erro": erro,
            "mensagem_sucesso": None,
            "mensagem_erro": erro_msg,
        }

    return {
        "ok": True,
        "medicao": medicao,
        "erro": None,
        "mensagem_sucesso": sucesso_msg,
        "mensagem_erro": None,
    }


def processar_submissao_form_medicao_update(
    *,
    form,
    empresa,
    sucesso_msg,
    erro_msg,
):
    if not form.is_valid():
        return {
            "ok": False,
            "medicao": None,
            "erro": None,
            "mensagem_sucesso": None,
            "mensagem_erro": erro_msg,
        }

    try:
        medicao = atualizar_medicao(form, empresa=empresa)
    except ValidationError as erro:
        form.add_error(None, erro)
        return {
            "ok": False,
            "medicao": None,
            "erro": erro,
            "mensagem_sucesso": None,
            "mensagem_erro": erro_msg,
        }

    return {
        "ok": True,
        "medicao": medicao,
        "erro": None,
        "mensagem_sucesso": sucesso_msg,
        "mensagem_erro": None,
    }


def processar_fluxo_form_medicao(
    *,
    method,
    post_data,
    files_data,
    form_class,
    empresa,
    furo,
    sucesso_msg,
    erro_msg,
    instance=None,
    acao="create",
):
    form_kwargs = {
        "furo": furo,
        "empresa": empresa,
    }
    if instance is not None:
        form_kwargs["instance"] = instance

    if method == "POST":
        form = form_class(post_data, files_data, **form_kwargs)
        if acao == "update":
            resultado = processar_submissao_form_medicao_update(
                form=form,
                empresa=empresa,
                sucesso_msg=sucesso_msg,
                erro_msg=erro_msg,
            )
        else:
            resultado = processar_submissao_form_medicao(
                form=form,
                empresa=empresa,
                furo=furo,
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
