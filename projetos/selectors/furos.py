from django.shortcuts import get_object_or_404

from projetos.models import ConfiguracaoPerfuracaoEmpregado, Furo, Medicao
from projetos.models import RegistoDiarioEmpregado



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


# TODO futuro:
# - centralizar filtros multiempresa num helper/base selector reutilizável
# - adicionar paginação/otimização quando o volume de furos crescer
# - avaliar cache em consultas de detalhe/3D muito frequentes



def _filtrar_por_empresa(queryset, empresa=None, campo="empresa_id"):
    if empresa is None:
        return queryset

    empresa_id = _resolver_empresa_id(empresa)
    return queryset.filter(**{campo: empresa_id})



def _decimal_para_float(valor):
    return float(valor) if valor is not None else None


def _formatar_horas_furo(total_horas_float):
    if not total_horas_float:
        return "-"
    return f"{float(total_horas_float):.2f} h"


def _obter_queryset_base_furos():
    return Furo.objects.select_related("projeto")



def _obter_queryset_base_configuracoes_perfuracao():
    return ConfiguracaoPerfuracaoEmpregado.objects.select_related(
        "empregado",
        "furo",
        "atualizado_por",
    )



def _serializar_furo_mapa(furo):
    return {
        "id": str(furo.id),
        "nome": furo.nome,
        "lat": _decimal_para_float(furo.latitude),
        "lon": _decimal_para_float(furo.longitude),
        "projeto": furo.projeto.nome if furo.projeto else "",
        "profundidade_atual": furo.profundidade_atual or 0,
        "profundidade_alvo_inicial": furo.profundidade_alvo_inicial or 0,
        "profundidade_alvo_atual": furo.profundidade_alvo_atual or 0,
        "inclinacao_planeada_inicial": (
            furo.inclinacao_planeada_inicial
            if furo.inclinacao_planeada_inicial is not None else "-"
        ),
        "inclinacao_planeada_atual": (
            furo.inclinacao_planeada_atual
            if furo.inclinacao_planeada_atual is not None else "-"
        ),
        "azimute_planeado_inicial": (
            furo.azimute_planeado_inicial
            if furo.azimute_planeado_inicial is not None else "-"
        ),
        "azimute_planeado_atual": (
            furo.azimute_planeado_atual
            if furo.azimute_planeado_atual is not None else "-"
        ),
        "inclinacao_real_atual": (
            furo.inclinacao_real_atual
            if furo.inclinacao_real_atual is not None else "-"
        ),
        "azimute_real_atual": (
            furo.azimute_real_atual
            if furo.azimute_real_atual is not None else "-"
        ),
    }



def obter_equipa_e_configuracao_por_furo(furo, empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    if empresa_id is not None and furo.empresa_id != empresa_id:
        return ConfiguracaoPerfuracaoEmpregado.objects.none()

    queryset = _obter_queryset_base_configuracoes_perfuracao().filter(furo=furo)

    if empresa_id is not None:
        queryset = queryset.filter(empresa_id=empresa_id)

    return queryset.order_by("empregado__nome")



def obter_lista_furos(empresa=None):
    queryset = _obter_queryset_base_furos().order_by("nome")
    return _filtrar_por_empresa(queryset, empresa)



def obter_furo(pk, empresa=None):
    queryset = _obter_queryset_base_furos()
    queryset = _filtrar_por_empresa(queryset, empresa)
    return get_object_or_404(queryset, pk=pk)



def obter_contexto_detalhe_furo(pk, empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    queryset = _obter_queryset_base_furos().prefetch_related(
        "medicoes",
        "registos_furo",
        "levantamentos_materiais",
    )
    queryset = _filtrar_por_empresa(queryset, empresa)

    furo = get_object_or_404(queryset, pk=pk)

    if empresa_id is not None and furo.empresa_id != empresa_id:
        return {
            "furo": furo,
            "medicoes": furo.medicoes.none(),
            "registos": furo.registos_furo.none(),
            "levantamentos": furo.levantamentos_materiais.none(),
            "furo_mapa": {},
        }

    medicoes = furo.medicoes.all().order_by("criado_em", "profundidade_medida")
    registos = (
        furo.registos_furo.select_related("empregado", "projeto")
        .all()
        .order_by("-data", "-criado_em")
    )
    levantamentos = (
        furo.levantamentos_materiais.select_related("empregado", "material", "projeto")
        .all()
    )

    if empresa_id is not None:
        medicoes = medicoes.filter(empresa_id=empresa_id, furo__empresa_id=empresa_id)
        registos = registos.filter(empresa_id=empresa_id, furo__empresa_id=empresa_id)
        levantamentos = levantamentos.filter(empresa_id=empresa_id, furo__empresa_id=empresa_id)

    total_horas_registos = round(
        sum(float(registo.horas_trabalhadas or 0) for registo in registos),
        2,
    )
    return {
        "furo": furo,
        "medicoes": medicoes,
        "registos": registos,
        "levantamentos": levantamentos,
        "furo_mapa": _serializar_furo_mapa(furo),
        "total_horas_registos": round(total_horas_registos, 2),
        "total_horas_registos_display": _formatar_horas_furo(total_horas_registos),
    }



def obter_medicoes_furo(furo, empresa=None):
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    if empresa_id is not None and furo.empresa_id != empresa_id:
        return Medicao.objects.none()

    queryset = Medicao.objects.filter(furo=furo).order_by("criado_em", "profundidade_medida")

    if empresa_id is not None:
        queryset = queryset.filter(empresa_id=empresa_id, furo__empresa_id=empresa_id)

    return queryset


def obter_configuracao_visual_furo(furo, empresa=None):
    queryset = ConfiguracaoPerfuracaoEmpregado.objects.filter(furo=furo)
    if empresa is not None:
        queryset = queryset.filter(empresa_id=_resolver_empresa_id(empresa))
    return queryset.order_by("-atualizado_em", "-pk").first()


def empregado_trabalhou_no_furo(empregado, furo):
    return empregado.registos_diarios.filter(
        furo=furo,
        empresa_id=empregado.empresa_id,
    ).exists()


def obter_registos_furo_para_empregado(empregado, furo):
    return (
        RegistoDiarioEmpregado.objects
        .filter(furo=furo, empresa_id=empregado.empresa_id)
        .select_related("empregado", "projeto", "furo")
        .order_by("-data", "-criado_em")
    )


def obter_medicoes_furo_para_empregado(empregado, furo):
    return (
        Medicao.objects
        .filter(furo=furo, empresa_id=empregado.empresa_id)
        .order_by("-criado_em", "-profundidade_medida")
    )


def obter_furo_opcional(empresa, pk):
    return Furo.objects.filter(pk=pk, empresa=empresa).first()
