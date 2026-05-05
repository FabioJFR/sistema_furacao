from datetime import date

from django.db import transaction
from django.core.exceptions import ValidationError

from projetos.models import Despesa, Projeto, SalarioBaseFuncao
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


def construir_contexto_relatorios_exportacao(*, request, empresa, listar_projetos_fn, listar_furos_fn, construir_cards_fn):
    filtros = construir_filtros_exportacao(request=request, empresa=empresa)
    return {
        "empresa": empresa,
        "datasets": construir_cards_fn(empresa, filtros),
        "projetos_filtro": listar_projetos_fn(empresa),
        "furos_filtro": listar_furos_fn(empresa=empresa, projeto=filtros.get("projeto")),
        "tipos_registo": [*TIPOS_REGISTO_CHOICES_EXPORTACAO],
        "categorias_despesa": [("", "Todas as categorias"), *Despesa.CATEGORIA_CHOICES],
        "filtros": filtros,
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


def processar_submissao_preferencias_admin_form(*, form, user, empresa):
    if not form.is_valid():
        return {
            "ok": False,
            "preferencias": None,
            "erros_form": form.errors,
        }
    preferencias = guardar_preferencias_admin(
        form=form,
        user=user,
        empresa=empresa,
    )
    return {
        "ok": True,
        "preferencias": preferencias,
        "erros_form": None,
    }


def processar_fluxo_preferencias_admin_form(
    *,
    method,
    post_data,
    form_class,
    preferencias,
    user,
    empresa,
):
    if method == "POST":
        form = form_class(post_data, instance=preferencias, user=user, prefix="prefs")
        resultado = processar_submissao_preferencias_admin_form(
            form=form,
            user=user,
            empresa=empresa,
        )
        return {
            "form": form,
            "resultado": resultado,
        }

    return {
        "form": form_class(instance=preferencias, user=user, prefix="prefs"),
        "resultado": None,
    }


def processar_submissao_financeiro_admin_form(*, financeiro_form):
    if not financeiro_form.is_valid():
        return {
            "ok": False,
            "empresa": None,
            "erros_form": financeiro_form.errors,
        }
    empresa = guardar_definicoes_financeiras_admin(financeiro_form=financeiro_form)
    return {
        "ok": True,
        "empresa": empresa,
        "erros_form": None,
    }


@transaction.atomic
def atualizar_financas_projeto(*, empresa, projeto_id, custo_por_metro, outros_gastos):
    projeto = Projeto.objects.filter(empresa=empresa, id=projeto_id).first()
    if not projeto:
        return {
            "ok": False,
            "erro": "Projeto não encontrado para esta empresa.",
        }

    if custo_por_metro in (None, ""):
        projeto.custo_por_metro_cliente_override = None
    else:
        try:
            valor = float(custo_por_metro)
        except (TypeError, ValueError):
            return {"ok": False, "erro": "Valor inválido para custo por metro."}
        if valor < 0:
            return {"ok": False, "erro": "O custo por metro do projeto não pode ser negativo."}
        projeto.custo_por_metro_cliente_override = valor

    if outros_gastos in (None, ""):
        projeto.outros_valores_gastos_associados = 0.0
    else:
        try:
            valor_outros = float(outros_gastos)
        except (TypeError, ValueError):
            return {"ok": False, "erro": "Valor inválido para outros gastos associados."}
        if valor_outros < 0:
            return {"ok": False, "erro": "Outros gastos associados não podem ser negativos."}
        projeto.outros_valores_gastos_associados = valor_outros

    try:
        projeto.save(
            update_fields=[
                "custo_por_metro_cliente_override",
                "outros_valores_gastos_associados",
                "atualizado_em",
            ]
        )
    except ValidationError as exc:
        return {"ok": False, "erro": str(exc)}

    empresa.recalcular_indicadores_financeiros()
    return {
        "ok": True,
        "mensagem": "Definições financeiras do projeto atualizadas com sucesso.",
    }


@transaction.atomic
def atualizar_salario_base_funcao(*, empresa, funcao, salario_base):
    funcao_valor = (funcao or "").strip()
    if not funcao_valor:
        return {"ok": False, "erro": "Função inválida."}

    try:
        salario = float(salario_base or 0)
    except (TypeError, ValueError):
        return {"ok": False, "erro": "Valor inválido para salário base."}

    if salario < 0:
        return {"ok": False, "erro": "O salário base não pode ser negativo."}

    obj, _ = SalarioBaseFuncao.objects.get_or_create(
        empresa=empresa,
        funcao=funcao_valor,
        defaults={"salario_base": salario},
    )
    if obj.salario_base != salario:
        obj.salario_base = salario
        obj.save(update_fields=["salario_base", "atualizado_em"])

    return {"ok": True, "mensagem": "Salário base da função atualizado com sucesso."}


def processar_fluxo_financeiro_admin_form(
    *,
    method,
    post_data,
    form_class,
    empresa,
):
    if method == "POST":
        financeiro_form = form_class(post_data, instance=empresa, prefix="financeiro")
        resultado = processar_submissao_financeiro_admin_form(financeiro_form=financeiro_form)
        return {
            "financeiro_form": financeiro_form,
            "resultado": resultado,
        }

    return {
        "financeiro_form": form_class(instance=empresa, prefix="financeiro"),
        "resultado": None,
    }
