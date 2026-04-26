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


@transaction.atomic
def apagar_projeto(*, projeto, empresa=None):
    _validar_projeto_empresa(projeto, empresa=empresa)
    projeto_id = projeto.pk
    projeto.delete()
    return projeto_id
