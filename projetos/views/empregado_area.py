import logging
import calendar
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from plataforma.models import MovimentoFinanceiroPlataforma, PagamentoEmpresa
from plataforma.selectors import obter_subscricao_atual_empresa
from projetos.decorators import empregado_required
from projetos.forms.empregado_area import MeusDadosEmpregadoForm
from projetos.services.acesso_contexto import obter_empregado_autenticado_contexto
from projetos.services.empregado_area import (
    atualizar_dados_empregado,
    atualizar_dados_individual,
)
from projetos.selectors.acesso import (
    obter_individual_por_user,
    resolver_empregado_por_user_ou_email,
)
from projetos.selectors.empregados import (
    obter_historico_projetos_empregado_area,
    obter_resumo_furos_empregado_area,
    obter_totais_empregado_area,
)

logger = logging.getLogger("core")


# ---------------- HELPERS ----------------
def _obter_empregado_autenticado_area(request):
    logger.debug(
        "A resolver empregado autenticado em empregado_area.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado, _ligado_por_fallback, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
        vincular_por_email=True,
    )
    if resposta_erro:
        logger.warning(
            "Utilizador sem contexto de empregado válido em empregado_area.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro

    return empregado, None


def _obter_individual_autenticado_area(request):
    logger.debug(
        "A resolver individual autenticado em empregado_area.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    individual = obter_individual_por_user(request.user)
    if not individual:
        logger.warning(
            "Utilizador autenticado sem registo em Individual em empregado_area.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "A tua conta individual não está configurada corretamente.")
        return None, redirect("projetos:redirect_after_login")

    return individual, None


def _normalizar_periodo_meses(ciclo):
    valor = str(ciclo or "").strip().lower()
    if valor == "mensal":
        return 1
    if valor == "anual":
        return 12
    try:
        inteiro = int(valor)
    except (TypeError, ValueError):
        return 1
    return inteiro if inteiro in [1, 3, 6, 12] else 1


def _adicionar_meses(data_base: date, meses: int):
    if not data_base:
        return None
    mes = data_base.month - 1 + meses
    ano = data_base.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data_base.day, calendar.monthrange(ano, mes)[1])
    return data_base.replace(year=ano, month=mes, day=dia)


def _obter_contexto_plano_pagamento(request, *, empregado=None):
    empresa_associada = getattr(empregado, "empresa", None) if empregado else None
    plano_atual = getattr(empresa_associada, "plano", None) if empresa_associada else None
    subscricao_atual = None
    data_inicio_plano = None
    data_fim_plano = None
    proximo_pagamento = None

    if empresa_associada:
        subscricao_atual = obter_subscricao_atual_empresa(empresa_associada)
        if subscricao_atual:
            if not plano_atual:
                plano_atual = subscricao_atual.plano
            data_inicio_plano = subscricao_atual.data_inicio
            data_fim_plano = subscricao_atual.data_fim
            proximo_pagamento = subscricao_atual.proxima_renovacao

        pagamento_empresa_pendente = (
            PagamentoEmpresa.objects.filter(
                empresa=empresa_associada,
                estado="pendente",
            )
            .exclude(data_vencimento__isnull=True)
            .order_by("data_vencimento", "criado_em")
            .first()
        )
        if pagamento_empresa_pendente:
            proximo_pagamento = pagamento_empresa_pendente.data_vencimento

    perfil = getattr(request.user, "perfil_plataforma", None)
    if perfil:
        movimento_com_plano = (
            MovimentoFinanceiroPlataforma.objects.filter(
                perfil_plataforma=perfil,
                plano__isnull=False,
                categoria__in=["subscricao", "renovacao", "pagamento_inicial"],
            )
            .select_related("plano")
            .order_by("-data_competencia", "-data_vencimento", "-criado_em")
            .first()
        )
        if movimento_com_plano and not plano_atual:
            plano_atual = movimento_com_plano.plano

        if movimento_com_plano and not data_inicio_plano:
            data_inicio_plano = movimento_com_plano.data_competencia or movimento_com_plano.criado_em.date()

        if movimento_com_plano and not data_fim_plano:
            data_fim_plano = movimento_com_plano.data_vencimento
            if (not data_fim_plano) and data_inicio_plano:
                data_fim_plano = _adicionar_meses(
                    data_inicio_plano,
                    _normalizar_periodo_meses(movimento_com_plano.ciclo_cobranca),
                )

        if movimento_com_plano and data_inicio_plano and data_fim_plano and data_fim_plano <= data_inicio_plano:
            data_fim_plano = _adicionar_meses(
                data_inicio_plano,
                _normalizar_periodo_meses(movimento_com_plano.ciclo_cobranca),
            )

        movimento_pendente = (
            MovimentoFinanceiroPlataforma.objects.filter(
                perfil_plataforma=perfil,
                natureza_fluxo="entrada",
                estado="pendente",
            )
            .exclude(data_vencimento__isnull=True)
            .order_by("data_vencimento", "criado_em")
            .first()
        )
        if movimento_pendente and not proximo_pagamento:
            proximo_pagamento = movimento_pendente.data_vencimento

    # Ajuste de consistência:
    # quando o próximo pagamento vem igual à criação da conta/movimento inicial,
    # deve refletir a data de renovação/fim do ciclo atual.
    if (
        data_inicio_plano
        and data_fim_plano
        and proximo_pagamento
        and data_fim_plano > data_inicio_plano
        and proximo_pagamento <= data_inicio_plano
    ):
        proximo_pagamento = data_fim_plano

    return {
        "empresa_associada": empresa_associada,
        "subscricao_atual": subscricao_atual,
        "plano_atual": plano_atual,
        "data_inicio_plano": data_inicio_plano,
        "data_fim_plano": data_fim_plano,
        "proximo_pagamento": proximo_pagamento,
    }


# Multiempresa: a área pessoal do empregado só pode mostrar e editar dados da sua própria empresa.
@login_required
@empregado_required
def meus_dados_empregado(request):
    logger.info(
        "Entrada na view meus_dados_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    perfil = getattr(request.user, "perfil_plataforma", None)
    if perfil and perfil.tipo_acesso == "individual":
        individual, resposta_erro = _obter_individual_autenticado_area(request)
        if resposta_erro:
            return resposta_erro

        empregado_individual, _ = resolver_empregado_por_user_ou_email(request.user)
        contexto_plano = _obter_contexto_plano_pagamento(
            request,
            empregado=empregado_individual,
        )

        context = {
            "individual": individual,
            "total_registos": individual.total_registos or 0,
            "total_horas": individual.total_horas or 0,
            "total_metros": individual.total_metros or 0,
            **contexto_plano,
        }
        return render(request, "projetos/meus_dados_individual.html", context)

    empregado, resposta_erro = _obter_empregado_autenticado_area(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view meus_dados_empregado. user_id=%s", request.user.id)
        return resposta_erro

    projetos_historico = obter_historico_projetos_empregado_area(empregado)
    furos_resumo = obter_resumo_furos_empregado_area(empregado)
    totais_area = obter_totais_empregado_area(empregado)
    contexto_plano = _obter_contexto_plano_pagamento(request, empregado=empregado)

    context = {
        "empregado": empregado,
        "projetos_historico": projetos_historico,
        "furos_resumo": furos_resumo,
        **totais_area,
        **contexto_plano,
    }

    logger.info(
        "View meus_dados_empregado carregada com sucesso. user_id=%s, empregado_id=%s, total_registos=%s",
        request.user.id,
        empregado.id,
        context["total_registos"],
    )
    return render(request, "projetos/meus_dados_empregado.html", context)


@login_required
@empregado_required
def meus_dados_empregado_editar(request):
    logger.info(
        "Entrada na view meus_dados_empregado_editar. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    perfil = getattr(request.user, "perfil_plataforma", None)
    if perfil and perfil.tipo_acesso == "individual":
        from projetos.forms.empregado_area import MeusDadosIndividualForm

        individual, resposta_erro = _obter_individual_autenticado_area(request)
        if resposta_erro:
            return resposta_erro

        if request.method == "POST":
            form = MeusDadosIndividualForm(request.POST, request.FILES, instance=individual)
            if form.is_valid():
                individual = atualizar_dados_individual(
                    form=form,
                    user=request.user,
                )
                messages.success(request, "Os teus dados foram atualizados com sucesso.")
                return redirect("projetos:meus_dados_empregado")

            messages.error(request, "Erro ao atualizar os teus dados.")
        else:
            form = MeusDadosIndividualForm(instance=individual)

        return render(request, "projetos/meus_dados_individual_editar.html", {
            "individual": individual,
            "form": form,
        })

    empregado, resposta_erro = _obter_empregado_autenticado_area(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view meus_dados_empregado_editar. user_id=%s", request.user.id)
        return resposta_erro

    if request.method == "POST":
        form = MeusDadosEmpregadoForm(
            request.POST,
            request.FILES,
            instance=empregado,
        )
        if form.is_valid():
            try:
                empregado = atualizar_dados_empregado(
                    form=form,
                    user=request.user,
                    empresa=empregado.empresa,
                )
            except ValidationError:
                messages.error(request, "Erro ao atualizar os teus dados.")
                return render(request, "projetos/meus_dados_empregado_editar.html", {
                    "empregado": empregado,
                    "form": form,
                })

            logger.info(
                "Dados do empregado atualizados com sucesso. user_id=%s, empregado_id=%s",
                request.user.id,
                empregado.id,
            )
            messages.success(request, "Os teus dados foram atualizados com sucesso.")
            return redirect("projetos:meus_dados_empregado")

        logger.warning(
            "Erro ao atualizar dados do empregado. user_id=%s, empregado_id=%s, erros=%s",
            request.user.id,
            empregado.id,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar os teus dados.")
    else:
        form = MeusDadosEmpregadoForm(instance=empregado)

    return render(request, "projetos/meus_dados_empregado_editar.html", {
        "empregado": empregado,
        "form": form,
    })
