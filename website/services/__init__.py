import calendar
from dataclasses import dataclass

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from plataforma.models import (
    Empresa,
    MovimentoFinanceiroPlataforma,
    PagamentoEmpresa,
    PerfilPlataforma,
    SubscricaoEmpresa,
)
from projetos.models import Individual
from website import selectors


@dataclass
class ResultadoRegisto:
    sucesso: bool
    erros: list[str]
    user_id: int | None = None
    tipo_conta: str | None = None


def adicionar_meses(data_base, meses):
    mes = data_base.month - 1 + meses
    ano = data_base.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data_base.day, calendar.monthrange(ano, mes)[1])
    return data_base.replace(year=ano, month=mes, day=dia)


def normalizar_periodo_cobranca(valor):
    try:
        periodo = int(valor or 1)
    except (TypeError, ValueError):
        periodo = 1
    return periodo if periodo in [1, 3, 6, 12] else 1


def obter_valor_plano_por_ciclo(plano, ciclo_subscricao):
    periodo_meses = normalizar_periodo_cobranca(ciclo_subscricao)
    if periodo_meses == 12 and plano.preco_anual:
        return plano.preco_anual or 0
    return (plano.preco_mensal or 0) * periodo_meses


def validar_pedido_registo(payload):
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    password1 = payload.get("password1") or ""
    password2 = payload.get("password2") or ""
    nome_empresa = (payload.get("nome_empresa") or "").strip()
    plano_id = payload.get("plano")
    tipo_conta = payload.get("tipo_conta") or "empresa"
    ciclo_subscricao = payload.get("ciclo_subscricao") or "1"

    erros = []

    if not username:
        erros.append("O username é obrigatório.")
    if User.objects.filter(username=username).exists():
        erros.append("Já existe um utilizador com esse username.")
    if email and User.objects.filter(email=email).exists():
        erros.append("Já existe um utilizador com esse email.")

    if not password1 or not password2:
        erros.append("A password é obrigatória.")
    elif password1 != password2:
        erros.append("As passwords não coincidem.")

    plano = selectors.obter_plano_ativo_por_id(plano_id)
    if not plano:
        erros.append("Seleciona um plano válido.")
    else:
        periodo_meses = normalizar_periodo_cobranca(ciclo_subscricao)
        if plano.tipo == "empresa" and tipo_conta != "empresa":
            erros.append("O plano escolhido exige conta do tipo empresa.")
        if plano.tipo == "individual" and tipo_conta != "individual":
            erros.append("O plano escolhido exige conta do tipo individual.")
        if periodo_meses not in plano.periodos_cobranca_disponiveis_normalizados:
            erros.append("Seleciona um período de pagamento válido para o plano escolhido.")
    if tipo_conta == "empresa" and not nome_empresa:
        erros.append("O nome da empresa é obrigatório para conta empresa.")

    return {"erros": erros, "plano": plano}


@transaction.atomic
def executar_registo(payload):
    validacao = validar_pedido_registo(payload)
    erros = validacao["erros"]
    plano = validacao["plano"]
    if erros:
        return ResultadoRegisto(sucesso=False, erros=erros)

    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    password1 = payload.get("password1") or ""
    nome_empresa = (payload.get("nome_empresa") or "").strip()
    nome_responsavel = (payload.get("nome_responsavel") or "").strip()
    tipo_conta = payload.get("tipo_conta") or "empresa"
    ciclo_subscricao = payload.get("ciclo_subscricao") or "1"

    valor_subscricao = obter_valor_plano_por_ciclo(plano, ciclo_subscricao)
    hoje = timezone.now().date()
    proxima_renovacao = adicionar_meses(hoje, normalizar_periodo_cobranca(ciclo_subscricao))

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password1,
        is_active=True,
    )

    empresa = None
    tipo_acesso = "individual"
    if tipo_conta == "empresa":
        empresa = Empresa.objects.create(
            nome=nome_empresa,
            nome_comercial=nome_empresa,
            email=email,
            responsavel_nome=nome_responsavel,
            responsavel_email=email,
            plano=plano,
            status="ativa",
            data_inicio=timezone.now().date(),
            ativo=True,
        )
        tipo_acesso = "empresa_admin"

    perfil = PerfilPlataforma.objects.create(
        user=user,
        tipo_acesso=tipo_acesso,
        empresa=empresa,
        ativo=True,
    )

    if tipo_conta == "individual":
        nome_individual = nome_responsavel or username
        Individual.objects.get_or_create(
            user=user,
            defaults={
                "nome": nome_individual,
                "email": email,
                "ativo": True,
            },
        )

    ciclo_normalizado = str(normalizar_periodo_cobranca(ciclo_subscricao))
    if tipo_conta == "empresa":
        subscricao = SubscricaoEmpresa.objects.create(
            empresa=empresa,
            plano=plano,
            estado="pendente",
            ciclo_cobranca=ciclo_normalizado,
            valor=valor_subscricao,
            data_inicio=hoje,
            data_fim=proxima_renovacao,
            proxima_renovacao=proxima_renovacao,
            renovacao_definida_manualmente=False,
            renovacao_automatica=False,
            observacoes="Subscrição inicial criada automaticamente no registo público.",
        )
        PagamentoEmpresa.objects.create(
            empresa=empresa,
            subscricao=subscricao,
            descricao="Cobrança inicial de registo",
            valor=valor_subscricao,
            data_vencimento=hoje,
            estado="pendente",
            observacoes="Registo automático para cobrança inicial da subscrição.",
        )
        MovimentoFinanceiroPlataforma.objects.create(
            empresa=empresa,
            plano=plano,
            subscricao=subscricao,
            tipo_movimento="cobranca",
            natureza_fluxo="entrada",
            categoria="subscricao",
            metodo_pagamento="manual",
            ciclo_cobranca=ciclo_normalizado,
            valor=valor_subscricao,
            valor_bruto=valor_subscricao,
            valor_liquido=valor_subscricao,
            descricao="Cobrança inicial criada no registo público",
            entidade_nome=empresa.nome,
            data_competencia=hoje,
            data_vencimento=hoje,
            estado="pendente",
            observacoes="Registo criado automaticamente para futura exportação e integração financeira.",
        )
    else:
        MovimentoFinanceiroPlataforma.objects.create(
            perfil_plataforma=perfil,
            plano=plano,
            tipo_movimento="cobranca",
            natureza_fluxo="entrada",
            categoria="subscricao",
            metodo_pagamento="manual",
            ciclo_cobranca=ciclo_normalizado,
            valor=valor_subscricao,
            valor_bruto=valor_subscricao,
            valor_liquido=valor_subscricao,
            descricao="Cobrança inicial de conta individual criada no registo público",
            entidade_nome=username,
            data_competencia=hoje,
            data_vencimento=hoje,
            estado="pendente",
            observacoes="Registo criado automaticamente para futura exportação e integração financeira.",
        )

    return ResultadoRegisto(sucesso=True, erros=[], user_id=user.id, tipo_conta=tipo_conta)
