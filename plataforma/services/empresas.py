from dataclasses import dataclass
from datetime import date, timedelta
import calendar

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from plataforma.models import Empresa, Plano


def adicionar_meses(data_base, meses):
    mes = data_base.month - 1 + meses
    ano = data_base.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data_base.day, calendar.monthrange(ano, mes)[1])
    return data_base.replace(year=ano, month=mes, day=dia)


def normalizar_periodo_meses(ciclo_cobranca):
    valor = str(ciclo_cobranca or "").strip()
    if valor == "mensal":
        return 1
    if valor == "anual":
        return 12
    try:
        meses = int(valor)
    except (TypeError, ValueError):
        meses = 1
    return meses if meses in [1, 3, 6, 12] else 1


def calcular_proxima_renovacao(data_inicio, ciclo_cobranca):
    return adicionar_meses(data_inicio, normalizar_periodo_meses(ciclo_cobranca))


def obter_valor_por_ciclo(plano, ciclo_cobranca):
    meses = normalizar_periodo_meses(ciclo_cobranca)
    if meses == 12 and plano.preco_anual:
        return plano.preco_anual or 0
    return (plano.preco_mensal or 0) * meses


def calcular_alerta_renovacao(subscricao_atual):
    if not subscricao_atual or not subscricao_atual.proxima_renovacao:
        return None
    hoje = timezone.now().date()
    if subscricao_atual.proxima_renovacao <= hoje:
        return "Renovação em atraso ou a vencer hoje."
    if subscricao_atual.proxima_renovacao <= (hoje + timedelta(days=7)):
        return "Renovação próxima nos próximos 7 dias."
    return None


@dataclass
class ResultadoAlteracaoPlano:
    ok: bool
    erro: str | None = None
    empresa: Empresa | None = None
    plano: Plano | None = None


@dataclass
class ResultadoRenovacaoSubscricao:
    ok: bool
    erro: str | None = None
    nova_data: date | None = None


@dataclass
class ResultadoSubmissaoAlteracaoPlano:
    ok: bool
    erro: str | None = None
    plano: Plano | None = None
    ciclo_subscricao: str | None = None


@transaction.atomic
def atualizar_renovacao_subscricao(subscricao_atual, nova_data: date):
    if not subscricao_atual:
        raise ValidationError("A empresa não tem subscrição ativa para atualizar a renovação.")
    if subscricao_atual.data_inicio and nova_data < subscricao_atual.data_inicio:
        raise ValidationError("A próxima renovação não pode ser anterior ao início da subscrição.")

    subscricao_atual.proxima_renovacao = nova_data
    subscricao_atual.data_fim = nova_data
    subscricao_atual.renovacao_definida_manualmente = True
    subscricao_atual.save(
        update_fields=[
            "proxima_renovacao",
            "data_fim",
            "renovacao_definida_manualmente",
            "atualizado_em",
        ]
    )
    return subscricao_atual


def processar_submissao_renovacao_subscricao(*, subscricao_atual, nova_data_raw):
    valor = str(nova_data_raw or "").strip()
    if not valor:
        return ResultadoRenovacaoSubscricao(
            ok=False,
            erro="Indique uma data para a próxima renovação.",
        )

    try:
        nova_data = date.fromisoformat(valor)
    except ValueError:
        return ResultadoRenovacaoSubscricao(
            ok=False,
            erro="A data indicada para a renovação é inválida.",
        )

    try:
        atualizar_renovacao_subscricao(subscricao_atual, nova_data)
    except Exception as exc:
        return ResultadoRenovacaoSubscricao(ok=False, erro=str(exc))

    return ResultadoRenovacaoSubscricao(ok=True, nova_data=nova_data)


def processar_fluxo_renovacao_subscricao(*, method, subscricao_atual, nova_data_raw):
    if method != "POST":
        return ResultadoRenovacaoSubscricao(
            ok=False,
            erro="metodo_invalido",
        )
    return processar_submissao_renovacao_subscricao(
        subscricao_atual=subscricao_atual,
        nova_data_raw=nova_data_raw,
    )


@transaction.atomic
def alterar_plano_empresa(*, empresa, subscricao_atual, novo_plano, ciclo_subscricao, estado_empresa):
    if ciclo_subscricao not in ["1", "3", "6", "12"]:
        return ResultadoAlteracaoPlano(ok=False, erro="Selecione um período de pagamento válido.")

    estados_empresa_validos = {valor for valor, _ in Empresa.STATUS_CHOICES}
    if estado_empresa not in estados_empresa_validos:
        return ResultadoAlteracaoPlano(ok=False, erro="Selecione um estado válido para a empresa.")

    if int(ciclo_subscricao) not in novo_plano.periodos_cobranca_disponiveis_normalizados:
        return ResultadoAlteracaoPlano(ok=False, erro="O plano selecionado não permite esse período de pagamento.")
    empresa.plano = novo_plano
    empresa.status = estado_empresa
    empresa.save(update_fields=["plano", "status", "atualizado_em"])

    if subscricao_atual:
        subscricao_atual.plano = novo_plano
        subscricao_atual.ciclo_cobranca = ciclo_subscricao
        subscricao_atual.valor = obter_valor_por_ciclo(novo_plano, ciclo_subscricao)

        if not subscricao_atual.renovacao_definida_manualmente:
            proxima_renovacao = calcular_proxima_renovacao(
                subscricao_atual.data_inicio,
                ciclo_subscricao,
            )
            subscricao_atual.proxima_renovacao = proxima_renovacao
            subscricao_atual.data_fim = proxima_renovacao

        subscricao_atual.save()

    return ResultadoAlteracaoPlano(ok=True, empresa=empresa, plano=novo_plano)


def processar_submissao_alteracao_plano_empresa(
    *,
    empresa,
    subscricao_atual,
    plano_id,
    ciclo_subscricao,
    estado_empresa,
    obter_plano_ativo_fn,
):
    novo_plano = obter_plano_ativo_fn(plano_id)
    resultado = alterar_plano_empresa(
        empresa=empresa,
        subscricao_atual=subscricao_atual,
        novo_plano=novo_plano,
        ciclo_subscricao=ciclo_subscricao,
        estado_empresa=estado_empresa,
    )
    if not resultado.ok:
        return ResultadoSubmissaoAlteracaoPlano(ok=False, erro=resultado.erro)

    return ResultadoSubmissaoAlteracaoPlano(
        ok=True,
        plano=novo_plano,
        ciclo_subscricao=ciclo_subscricao,
    )


def processar_fluxo_alteracao_plano_empresa(
    *,
    method,
    empresa,
    subscricao_atual,
    plano_id,
    ciclo_subscricao,
    estado_empresa,
    obter_plano_ativo_fn,
):
    if method != "POST":
        return ResultadoSubmissaoAlteracaoPlano(
            ok=False,
            erro="metodo_invalido",
        )
    return processar_submissao_alteracao_plano_empresa(
        empresa=empresa,
        subscricao_atual=subscricao_atual,
        plano_id=plano_id,
        ciclo_subscricao=ciclo_subscricao,
        estado_empresa=estado_empresa,
        obter_plano_ativo_fn=obter_plano_ativo_fn,
    )


@transaction.atomic
def toggle_ativa_empresa(empresa):
    empresa.ativo = not empresa.ativo
    if empresa.ativo:
        if empresa.status in ["suspensa", "cancelada"]:
            empresa.status = "ativa"
        mensagem = f"Empresa '{empresa.nome}' reativada com sucesso."
    else:
        empresa.status = "suspensa"
        mensagem = f"Empresa '{empresa.nome}' suspensa com sucesso."

    empresa.save(update_fields=["ativo", "status", "atualizado_em"])
    return empresa, mensagem


def processar_fluxo_toggle_ativa_empresa(*, method, empresa):
    if method != "POST":
        return {
            "ok": False,
            "erro": "metodo_invalido",
            "empresa": empresa,
            "mensagem": None,
        }

    empresa_atualizada, mensagem = toggle_ativa_empresa(empresa)
    return {
        "ok": True,
        "erro": None,
        "empresa": empresa_atualizada,
        "mensagem": mensagem,
    }
