from datetime import timedelta
from django.utils import timezone
from django.db.models import Min

from django.core.exceptions import ValidationError
from django.db import transaction

from projetos.models import Furo, RegistoDiarioEmpregado
from projetos.services.furo_versioning import registar_versao_furo



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _atribuir_empresa_furo(furo, empresa=None):
    if empresa is None:
        return furo

    furo.empresa_id = _resolver_empresa_id(empresa)
    return furo



def validar_empresa_furo(furo, empresa=None):
    if not furo.empresa_id:
        raise ValidationError("O furo deve estar associado a uma empresa.")

    if not furo.projeto_id:
        raise ValidationError("O furo deve estar associado a um projeto.")

    if furo.projeto.empresa_id != furo.empresa_id:
        raise ValidationError("O projeto do furo deve pertencer à mesma empresa.")

    if empresa is not None:
        empresa_id = _resolver_empresa_id(empresa)
        if furo.empresa_id != empresa_id:
            raise ValidationError("O furo não pertence à empresa atual.")



def normalizar_campos_base_furo(furo):
    # Coordenadas base
    furo.origem_este = furo.origem_este or 0.0
    furo.origem_norte = furo.origem_norte or 0.0
    furo.origem_tvd = furo.origem_tvd or 0.0

    # Garantir que os campos "atuais" do planeamento não ficam vazios
    if furo.profundidade_alvo_atual is None:
        furo.profundidade_alvo_atual = furo.profundidade_alvo_inicial

    if furo.inclinacao_planeada_atual is None:
        furo.inclinacao_planeada_atual = furo.inclinacao_planeada_inicial

    if furo.azimute_planeado_atual is None:
        furo.azimute_planeado_atual = furo.azimute_planeado_inicial

    return furo



def _garantir_coerencia_profundidades_furo(furo):
    profundidade_atual = furo.profundidade_atual or 0.0
    profundidade_maxima = furo.profundidade_maxima_atingida or 0.0

    if profundidade_maxima < profundidade_atual:
        furo.profundidade_maxima_atingida = profundidade_atual

    return furo



def _inicializar_estado_real_furo(furo):
    if furo.inclinacao_real_atual is None:
        furo.inclinacao_real_atual = furo.inclinacao_planeada_inicial

    if furo.azimute_real_atual is None:
        furo.azimute_real_atual = furo.azimute_planeado_inicial

    return furo



def _sem_medicoes_e_registos(furo, empresa_id=None):
    medicoes_qs = furo.medicoes.all()
    registos_qs = furo.registos_furo.all()

    if empresa_id is not None:
        medicoes_qs = medicoes_qs.filter(empresa_id=empresa_id)
        registos_qs = registos_qs.filter(empresa_id=empresa_id)

    return not medicoes_qs.exists() and not registos_qs.exists()



def _preparar_furo_novo(furo, empresa=None):
    # TODO futuro:
    # - mover regras comuns de preparação para uma camada base reutilizável
    # - adicionar auditoria de criação/alteração do furo
    _atribuir_empresa_furo(furo, empresa=empresa)
    validar_empresa_furo(furo, empresa=empresa)
    normalizar_campos_base_furo(furo)

    # Profundidade atual arranca na profundidade inicial
    furo.profundidade_atual = furo.profundidade_inicial or 0.0

    # Profundidade máxima atingida arranca na profundidade atual
    _garantir_coerencia_profundidades_furo(furo)

    # Estado real inicial pode arrancar com o planeado inicial
    _inicializar_estado_real_furo(furo)

    return furo



def _preparar_furo_para_atualizacao(furo, empresa=None):
    # TODO futuro:
    # - centralizar regras de atualização do furo num serviço/base class
    # - auditar alterações críticas de profundidade e planeamento
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    _atribuir_empresa_furo(furo, empresa=empresa)
    validar_empresa_furo(furo, empresa=empresa)
    normalizar_campos_base_furo(furo)
    _garantir_coerencia_profundidades_furo(furo)

    # Se não existirem medições nem registos, manter o furo num estado inicial coerente
    if _sem_medicoes_e_registos(furo, empresa_id=empresa_id):
        furo.profundidade_atual = furo.profundidade_inicial or 0.0
        furo.profundidade_maxima_atingida = furo.profundidade_atual

    return furo



@transaction.atomic
def criar_furo(form, empresa):
    furo = form.save(commit=False)
    furo = _preparar_furo_novo(furo, empresa=empresa)

    furo.save()
    registar_versao_furo(furo, origem="criado")
    form.save_m2m()
    return furo



@transaction.atomic
def atualizar_furo(form, empresa):
    furo = form.save(commit=False)
    furo = _preparar_furo_para_atualizacao(furo, empresa=empresa)

    furo.save()
    registar_versao_furo(furo, origem="atualizado")
    form.save_m2m()
    return furo


@transaction.atomic
def apagar_furo(*, furo, empresa=None):
    validar_empresa_furo(furo, empresa=empresa)
    furo_id = furo.pk
    furo.delete()
    return furo_id


# Nota de arquitetura:
# A lógica de criação/edição de medições foi centralizada em `projetos.services.medicoes`.
# Este service de furos mantém apenas regras próprias do furo e o recálculo baseado nos
# registos de produção, que continuam a ser a fonte de verdade para a profundidade atual.
@transaction.atomic
def recalcular_resumo_furo(furo):
    validar_empresa_furo(furo, empresa=furo.empresa_id)
    registos = (
        RegistoDiarioEmpregado.objects.filter(furo=furo, empresa_id=furo.empresa_id)
        .order_by("data", "criado_em")
    )

    profundidade_corrente = furo.profundidade_inicial or 0.0
    profundidade_maxima = profundidade_corrente
    total_horas = timedelta()
    data_inicio_operacao = None

    registos_para_atualizar = []

    for registo in registos:
        data_ref = registo.data or (registo.criado_em.date() if registo.criado_em else None)
        if data_ref and (data_inicio_operacao is None or data_ref < data_inicio_operacao):
            data_inicio_operacao = data_ref

        metros_turno = registo.metros_furados or 0.0

        profundidade_antes = profundidade_corrente
        profundidade_depois = profundidade_antes + metros_turno

        alterou = False

        if registo.profundidade_furo_antes != profundidade_antes:
            registo.profundidade_furo_antes = profundidade_antes
            alterou = True

        if registo.profundidade_furo_depois != profundidade_depois:
            registo.profundidade_furo_depois = profundidade_depois
            alterou = True

        if alterou:
            registos_para_atualizar.append(registo)

        profundidade_corrente = profundidade_depois

        if profundidade_corrente > profundidade_maxima:
            profundidade_maxima = profundidade_corrente

        total_horas += registo.horas_trabalhadas_furo or timedelta()

    if registos_para_atualizar:
        RegistoDiarioEmpregado.objects.bulk_update(
            registos_para_atualizar,
            ["profundidade_furo_antes", "profundidade_furo_depois"],
        )

    furo.profundidade_atual = profundidade_corrente
    furo.profundidade_maxima_atingida = profundidade_maxima
    furo.total_horas = total_horas
    if data_inicio_operacao:
        furo.data_inicio_operacao = data_inicio_operacao

    # Recalcular o resumo não deve falhar por validações históricas de outros
    # campos do furo que não estão a ser alterados neste processo.
    update_data = {
        "profundidade_atual": profundidade_corrente,
        "profundidade_maxima_atingida": profundidade_maxima,
        "total_horas": total_horas,
        "data_inicio_operacao": furo.data_inicio_operacao,
    }
    Furo.objects.filter(pk=furo.pk).update(**update_data)
    registar_versao_furo(furo, origem="recalculo")

    return furo


@transaction.atomic
def terminar_furo(*, furo, empresa=None, terminado_por=None):
    validar_empresa_furo(furo, empresa=empresa)
    hoje = timezone.now().date()
    primeiro_registo = (
        RegistoDiarioEmpregado.objects.filter(furo=furo, empresa_id=furo.empresa_id)
        .aggregate(data_min=Min("data"))
        .get("data_min")
    )
    data_inicio_operacao = primeiro_registo or furo.data_inicio_operacao

    Furo.objects.filter(pk=furo.pk).update(
        estado="concluido",
        data_inicio_operacao=data_inicio_operacao,
        data_fim_operacao=hoje,
    )
    furo.refresh_from_db()
    registar_versao_furo(furo, origem="concluido", criado_por=terminado_por)
    return furo


@transaction.atomic
def reativar_furo(*, furo, empresa=None):
    validar_empresa_furo(furo, empresa=empresa)

    Furo.objects.filter(pk=furo.pk).update(
        estado="ativo",
        data_fim_operacao=None,
    )
    furo.refresh_from_db()
    registar_versao_furo(furo, origem="reativado")
    return furo


def processar_acao_terminar_furo(*, request_method, furo, empresa=None, terminado_por=None):
    if request_method != "POST":
        return {
            "ok": False,
            "mensagem_sucesso": None,
            "mensagem_erro": None,
            "deve_redirecionar_legacy": True,
            "furo": furo,
        }

    furo_atualizado = terminar_furo(
        furo=furo,
        empresa=empresa,
        terminado_por=terminado_por,
    )
    return {
        "ok": True,
        "mensagem_sucesso": "Furo terminado com sucesso.",
        "mensagem_erro": None,
        "deve_redirecionar_legacy": False,
        "furo": furo_atualizado,
    }


def processar_acao_reativar_furo(*, request_method, furo, empresa=None):
    if request_method != "POST":
        return {
            "ok": False,
            "mensagem_sucesso": None,
            "mensagem_erro": None,
            "deve_redirecionar_legacy": True,
            "furo": furo,
        }

    furo_atualizado = reativar_furo(
        furo=furo,
        empresa=empresa,
    )
    return {
        "ok": True,
        "mensagem_sucesso": "Furo reativado com sucesso.",
        "mensagem_erro": None,
        "deve_redirecionar_legacy": False,
        "furo": furo_atualizado,
    }
