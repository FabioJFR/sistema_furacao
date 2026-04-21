from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone

from plataforma.decorators import platform_admin_required
from plataforma.models import Empresa, MovimentoFinanceiroPlataforma, Plano, SubscricaoEmpresa

# TODO futuro:
# - ligar com subscrição (SubscricaoEmpresa)
# - mostrar histórico de pagamentos
# - bloquear funcionalidades quando plano expira
# - mostrar consumo vs limites do plano (furos, empregados, armazenamento)
# - registar histórico de mudança de plano por empresa
# - auditar suspensão/reativação de empresa
# - impedir suspensão quando existirem operações críticas pendentes


# TODO futuro:
# - substituir este padrão por serviços/selectors dedicados para empresas da plataforma
# - separar ações críticas (alterar plano, suspender) em services próprios


def _adicionar_meses(data_base, meses):
    import calendar

    mes = data_base.month - 1 + meses
    ano = data_base.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data_base.day, calendar.monthrange(ano, mes)[1])
    return data_base.replace(year=ano, month=mes, day=dia)


def _calcular_proxima_renovacao(data_inicio, ciclo_cobranca):
    valor = str(ciclo_cobranca or "").strip()
    if valor == "mensal":
        meses = 1
    elif valor == "anual":
        meses = 12
    else:
        try:
            meses = int(valor)
        except (TypeError, ValueError):
            meses = 1
    return _adicionar_meses(data_inicio, meses)


def _obter_valor_por_ciclo(plano, ciclo_cobranca):
    valor = str(ciclo_cobranca or "").strip()
    if valor == "mensal":
        meses = 1
    elif valor == "anual":
        meses = 12
    else:
        try:
            meses = int(valor)
        except (TypeError, ValueError):
            meses = 1
    if meses == 12 and plano.preco_anual:
        return plano.preco_anual or 0
    return (plano.preco_mensal or 0) * meses

@login_required
@platform_admin_required
def empresa_detail_plataforma(request, pk):
    perfil = request.perfil_plataforma

    empresa = get_object_or_404(
        Empresa.objects.select_related("plano"),
        pk=pk,
    )
    subscricao_atual = (
        SubscricaoEmpresa.objects
        .select_related("plano")
        .filter(empresa=empresa)
        .order_by("-data_inicio", "-criado_em")
        .first()
    )
    movimentos_financeiros = (
        MovimentoFinanceiroPlataforma.objects
        .select_related("plano", "subscricao")
        .filter(empresa=empresa)
        .order_by("-data_vencimento", "-criado_em")[:5]
    )
    alerta_renovacao = None
    if subscricao_atual and subscricao_atual.proxima_renovacao:
        hoje = timezone.now().date()
        if subscricao_atual.proxima_renovacao <= hoje:
            alerta_renovacao = "Renovação em atraso ou a vencer hoje."
        elif subscricao_atual.proxima_renovacao <= (hoje + timedelta(days=7)):
            alerta_renovacao = "Renovação próxima nos próximos 7 dias."

    # =========================
    # MÉTRICAS BASE (placeholder para evolução)
    # =========================

    # TODO futuro: substituir por queries reais (projetos, furos, empregados)
    total_projetos = 0
    total_furos = 0
    total_empregados = 0

    # =========================
    # CONTEXTO
    # =========================

    context = {
        "empresa": empresa,
        "perfil": perfil,

        # métricas
        "total_projetos": total_projetos,
        "total_furos": total_furos,
        "total_empregados": total_empregados,
        "subscricao_atual": subscricao_atual,
        "movimentos_financeiros": movimentos_financeiros,
        "alerta_renovacao": alerta_renovacao,
    }

    return render(request, "plataforma/empresa_detail.html", context)


@login_required
@platform_admin_required
def atualizar_renovacao_subscricao_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)

    if request.method != "POST":
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    subscricao_atual = (
        SubscricaoEmpresa.objects
        .filter(empresa=empresa)
        .order_by("-data_inicio", "-criado_em")
        .first()
    )

    if not subscricao_atual:
        messages.error(request, "A empresa não tem subscrição ativa para atualizar a renovação.")
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    nova_data_raw = (request.POST.get("proxima_renovacao") or "").strip()
    if not nova_data_raw:
        messages.error(request, "Indique uma data para a próxima renovação.")
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    try:
        nova_data = date.fromisoformat(nova_data_raw)
    except ValueError:
        messages.error(request, "A data indicada para a renovação é inválida.")
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    if subscricao_atual.data_inicio and nova_data < subscricao_atual.data_inicio:
        messages.error(request, "A próxima renovação não pode ser anterior ao início da subscrição.")
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

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

    messages.success(
        request,
        f"Próxima renovação da empresa '{empresa.nome}' atualizada para {nova_data.strftime('%d/%m/%Y')}.",
    )
    return redirect("plataforma:empresa_detail", pk=empresa.pk)


@login_required
@platform_admin_required
def alterar_plano_empresa(request, pk):
    perfil = request.perfil_plataforma

    empresa = get_object_or_404(
        Empresa.objects.select_related("plano"),
        pk=pk,
    )

    planos = Plano.objects.filter(ativo=True).order_by("tipo", "preco_mensal", "nome")
    subscricao_atual = (
        SubscricaoEmpresa.objects
        .select_related("plano")
        .filter(empresa=empresa)
        .order_by("-data_inicio", "-criado_em")
        .first()
    )

    if request.method == "POST":
        plano_id = request.POST.get("plano")
        ciclo_subscricao = (request.POST.get("ciclo_subscricao") or "1").strip()
        estado_empresa = (request.POST.get("estado_empresa") or empresa.status or "teste").strip()
        novo_plano = get_object_or_404(Plano, pk=plano_id, ativo=True)

        estados_empresa_validos = {valor for valor, _ in Empresa.STATUS_CHOICES}

        if ciclo_subscricao not in ["1", "3", "6", "12"]:
            messages.error(request, "Selecione um período de pagamento válido.")
            return redirect("plataforma:empresa_alterar_plano", pk=empresa.pk)

        if estado_empresa not in estados_empresa_validos:
            messages.error(request, "Selecione um estado válido para a empresa.")
            return redirect("plataforma:empresa_alterar_plano", pk=empresa.pk)

        if int(ciclo_subscricao) not in novo_plano.periodos_cobranca_disponiveis_normalizados:
            messages.error(request, "O plano selecionado não permite esse período de pagamento.")
            return redirect("plataforma:empresa_alterar_plano", pk=empresa.pk)

        if int(ciclo_subscricao) in [1, 3, 6] and not novo_plano.preco_mensal:
            messages.error(request, "O plano selecionado precisa de preço mensal para esse período.")
            return redirect("plataforma:empresa_alterar_plano", pk=empresa.pk)

        if int(ciclo_subscricao) == 12 and not novo_plano.preco_anual and not novo_plano.preco_mensal:
            messages.error(request, "O plano selecionado precisa de preço anual ou mensal para 12 meses.")
            return redirect("plataforma:empresa_alterar_plano", pk=empresa.pk)

        empresa.plano = novo_plano
        empresa.status = estado_empresa
        empresa.save()

        if subscricao_atual:
            subscricao_atual.plano = novo_plano
            subscricao_atual.ciclo_cobranca = ciclo_subscricao
            subscricao_atual.valor = _obter_valor_por_ciclo(novo_plano, ciclo_subscricao)

            if not subscricao_atual.renovacao_definida_manualmente:
                proxima_renovacao = _calcular_proxima_renovacao(
                    subscricao_atual.data_inicio,
                    ciclo_subscricao,
                )
                subscricao_atual.proxima_renovacao = proxima_renovacao
                subscricao_atual.data_fim = proxima_renovacao

            subscricao_atual.save()

        messages.success(
            request,
            f"Plano da empresa '{empresa.nome}' alterado para '{novo_plano.nome}' com período de {ciclo_subscricao} mês(es).",
        )
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    context = {
        "empresa": empresa,
        "perfil": perfil,
        "planos": planos,
        "subscricao_atual": subscricao_atual,
        "estados_empresa": Empresa.STATUS_CHOICES,
        "titulo": f"Alterar Plano - {empresa.nome}",
    }

    return render(request, "plataforma/empresa_alterar_plano.html", context)


@login_required
@platform_admin_required
def toggle_empresa_ativa(request, pk):
    perfil = request.perfil_plataforma

    empresa = get_object_or_404(Empresa, pk=pk)

    if request.method != "POST":
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    empresa.ativo = not empresa.ativo

    if empresa.ativo:
        if empresa.status in ["suspensa", "cancelada"]:
            empresa.status = "ativa"
        mensagem = f"Empresa '{empresa.nome}' reativada com sucesso."
    else:
        empresa.status = "suspensa"
        mensagem = f"Empresa '{empresa.nome}' suspensa com sucesso."

    empresa.save(update_fields=["ativo", "status", "atualizado_em"])

    messages.success(request, mensagem)
    return redirect("plataforma:empresa_detail", pk=empresa.pk)
