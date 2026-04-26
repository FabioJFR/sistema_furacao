from datetime import date

from django.db import transaction

from projetos.models import Despesa
from projetos.selectors.opcoes import obter_projeto_furo_filtros_exportacao
from projetos.services.acesso_contexto import obter_empresa_admin_contexto


TIPOS_REGISTO_CHOICES_EXPORTACAO = [
    ("", "Todos os registos"),
    ("sem_paragem", "Sem paragem"),
    ("cliente", "Paragem do cliente"),
    ("empresa", "Paragem da empresa"),
]


def obter_empresa_admin_opcoes(*, request):
    return obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )


def parse_data_iso(valor):
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def construir_filtros_exportacao(*, request, empresa):
    projeto_id = (request.GET.get("projeto") or "").strip()
    furo_id = (request.GET.get("furo") or "").strip()
    tipo_registo = (request.GET.get("tipo_registo") or "").strip()
    categoria_despesa = (request.GET.get("categoria_despesa") or "").strip()
    data_inicio = parse_data_iso(request.GET.get("data_inicio"))
    data_fim = parse_data_iso(request.GET.get("data_fim"))
    projeto, furo = obter_projeto_furo_filtros_exportacao(
        empresa=empresa,
        projeto_id=projeto_id,
        furo_id=furo_id,
    )
    return {
        "projeto": projeto,
        "furo": furo,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "tipo_registo": tipo_registo,
        "categoria_despesa": categoria_despesa,
        "tipo_registo_label": dict(TIPOS_REGISTO_CHOICES_EXPORTACAO).get(tipo_registo, tipo_registo),
        "categoria_despesa_label": dict(Despesa.CATEGORIA_CHOICES).get(categoria_despesa, categoria_despesa),
    }


@transaction.atomic
def guardar_preferencias_admin(*, form, user, empresa):
    preferencias = form.save(commit=False)
    preferencias.user = user
    preferencias.empresa = empresa
    preferencias.save()
    return preferencias


@transaction.atomic
def guardar_definicoes_financeiras_admin(*, financeiro_form):
    empresa = financeiro_form.save()
    empresa.recalcular_indicadores_financeiros()
    return empresa
