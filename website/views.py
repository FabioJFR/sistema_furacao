from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from django.contrib.auth import logout

from plataforma.models import (
    Empresa,
    MovimentoFinanceiroPlataforma,
    PagamentoEmpresa,
    PerfilPlataforma,
    Plano,
    SubscricaoEmpresa,
)


def _adicionar_meses(data_base, meses):
    import calendar

    mes = data_base.month - 1 + meses
    ano = data_base.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data_base.day, calendar.monthrange(ano, mes)[1])
    return data_base.replace(year=ano, month=mes, day=dia)


def _normalizar_periodo_cobranca(valor):
    try:
        periodo = int(valor or 1)
    except (TypeError, ValueError):
        periodo = 1
    return periodo if periodo in [1, 3, 6, 12] else 1


def _obter_valor_plano_por_ciclo(plano, ciclo_subscricao):
    periodo_meses = _normalizar_periodo_cobranca(ciclo_subscricao)
    if periodo_meses == 12 and plano.preco_anual:
        return plano.preco_anual or 0
    return (plano.preco_mensal or 0) * periodo_meses


def _obter_planos_contexto(planos_qs):
    return {
        str(plano.pk): {
            "nome": plano.nome,
            "tipo": plano.tipo,
            "periodos": plano.periodos_cobranca_disponiveis_normalizados,
            "preco_mensal": str(plano.preco_mensal or 0),
            "preco_anual": str(plano.preco_anual or 0),
        }
        for plano in planos_qs
    }


def home(request):
    planos = Plano.objects.filter(ativo=True).order_by("preco_mensal")
    return render(
        request,
        "website/home.html",
        {
            "planos": planos[:3],
        },
    )


def planos(request):
    planos_qs = Plano.objects.filter(ativo=True).order_by("preco_mensal")
    return render(
        request,
        "website/planos.html",
        {
            "planos": planos_qs,
        },
    )


@transaction.atomic
def registo(request):
    planos_qs = Plano.objects.filter(ativo=True).order_by("preco_mensal")
    planos_contexto = _obter_planos_contexto(planos_qs)

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password1 = request.POST.get("password1") or ""
        password2 = request.POST.get("password2") or ""
        nome_empresa = (request.POST.get("nome_empresa") or "").strip()
        nome_responsavel = (request.POST.get("nome_responsavel") or "").strip()
        plano_id = request.POST.get("plano")
        tipo_conta = request.POST.get("tipo_conta") or "empresa"
        ciclo_subscricao = request.POST.get("ciclo_subscricao") or "1"

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

        plano = Plano.objects.filter(pk=plano_id, ativo=True).first()
        if not plano:
            erros.append("Seleciona um plano válido.")
        else:
            periodo_meses = _normalizar_periodo_cobranca(ciclo_subscricao)

            if plano.tipo == "empresa" and tipo_conta != "empresa":
                erros.append("O plano escolhido exige conta do tipo empresa.")

            if plano.tipo == "individual" and tipo_conta != "individual":
                erros.append("O plano escolhido exige conta do tipo individual.")

            if periodo_meses not in plano.periodos_cobranca_disponiveis_normalizados:
                erros.append("Seleciona um período de pagamento válido para o plano escolhido.")

            if periodo_meses in [1, 3, 6] and not plano.preco_mensal:
                erros.append("O plano escolhido precisa de preço mensal para esse período.")

            if periodo_meses == 12 and not plano.preco_anual and not plano.preco_mensal:
                erros.append("O plano escolhido precisa de preço anual ou mensal para 12 meses.")

        if tipo_conta == "empresa" and not nome_empresa:
            erros.append("O nome da empresa é obrigatório para conta empresa.")

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(
                request,
                "website/registo.html",
                {
                    "planos": planos_qs,
                    "dados": request.POST,
                    "planos_contexto": planos_contexto,
                },
            )

        valor_subscricao = _obter_valor_plano_por_ciclo(plano, ciclo_subscricao)
        hoje = timezone.now().date()
        proxima_renovacao = _adicionar_meses(hoje, _normalizar_periodo_cobranca(ciclo_subscricao))

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

        if tipo_conta == "empresa":
            subscricao = SubscricaoEmpresa.objects.create(
                empresa=empresa,
                plano=plano,
                estado="pendente",
                ciclo_cobranca=str(_normalizar_periodo_cobranca(ciclo_subscricao)),
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
                ciclo_cobranca=str(_normalizar_periodo_cobranca(ciclo_subscricao)),
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
                ciclo_cobranca=str(_normalizar_periodo_cobranca(ciclo_subscricao)),
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

        messages.success(
            request,
            "Conta criada com sucesso. Já podes iniciar sessão.",
        )
        return redirect("login")

    return render(
        request,
        "website/registo.html",
        {
            "planos": planos_qs,
            "planos_contexto": planos_contexto,
        },
    )


def logout_user(request):
    logout(request)
    return redirect("website:home")
