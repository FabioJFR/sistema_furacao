from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from plataforma.decorators import platform_admin_required
from plataforma.models import Empresa
from plataforma.selectors.empresas import (
    listar_movimentos_financeiros_empresa,
    obter_empresa,
    obter_empresa_com_plano,
    obter_subscricao_atual_empresa,
)
from plataforma.selectors.planos import (
    construir_contexto_trial_plano,
    enriquecer_planos_com_contexto_trial,
    listar_planos_para_admin,
    obter_plano_ativo,
)
from plataforma.services import empresas as empresas_service

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
@login_required
@platform_admin_required
def empresa_detail_plataforma(request, pk):
    perfil = request.perfil_plataforma

    empresa = obter_empresa_com_plano(pk)
    subscricao_atual = obter_subscricao_atual_empresa(empresa)
    movimentos_financeiros = listar_movimentos_financeiros_empresa(empresa, limit=5)
    context = empresas_service.construir_contexto_empresa_detail(
        empresa=empresa,
        perfil=perfil,
        subscricao_atual=subscricao_atual,
        movimentos_financeiros=movimentos_financeiros,
        plano_trial_contexto=construir_contexto_trial_plano(getattr(empresa, "plano", None)),
    )

    return render(request, "plataforma/empresa_detail.html", context)


@login_required
@platform_admin_required
def atualizar_renovacao_subscricao_empresa(request, pk):
    empresa = obter_empresa(pk)
    subscricao_atual = obter_subscricao_atual_empresa(empresa)
    resultado = empresas_service.processar_fluxo_renovacao_subscricao(
        method=request.method,
        subscricao_atual=subscricao_atual,
        nova_data_raw=request.POST.get("proxima_renovacao"),
    )
    if not resultado.ok:
        if resultado.erro == "metodo_invalido":
            return redirect("plataforma:empresa_detail", pk=empresa.pk)
        messages.error(request, resultado.erro)
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    messages.success(
        request,
        f"Próxima renovação da empresa '{empresa.nome}' atualizada para {resultado.nova_data.strftime('%d/%m/%Y')}.",
    )
    return redirect("plataforma:empresa_detail", pk=empresa.pk)


@login_required
@platform_admin_required
def alterar_plano_empresa(request, pk):
    perfil = request.perfil_plataforma

    empresa = obter_empresa_com_plano(pk)
    planos = listar_planos_para_admin()
    enriquecer_planos_com_contexto_trial(planos)
    subscricao_atual = obter_subscricao_atual_empresa(empresa)

    if request.method == "POST":
        resultado = empresas_service.processar_fluxo_alteracao_plano_empresa(
            method=request.method,
            empresa=empresa,
            subscricao_atual=subscricao_atual,
            plano_id=request.POST.get("plano"),
            ciclo_subscricao=(request.POST.get("ciclo_subscricao") or "1").strip(),
            estado_empresa=(request.POST.get("estado_empresa") or empresa.status or "teste").strip(),
            obter_plano_ativo_fn=obter_plano_ativo,
        )
        if not resultado.ok:
            if resultado.erro == "metodo_invalido":
                return redirect("plataforma:empresa_alterar_plano", pk=empresa.pk)
            messages.error(request, resultado.erro)
            return redirect("plataforma:empresa_alterar_plano", pk=empresa.pk)

        messages.success(
            request,
            f"Plano da empresa '{empresa.nome}' alterado para '{resultado.plano.nome}' com período de {resultado.ciclo_subscricao} mês(es).",
        )
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    context = empresas_service.construir_contexto_alterar_plano_empresa(
        empresa=empresa,
        perfil=perfil,
        planos=planos,
        subscricao_atual=subscricao_atual,
        estados_empresa=Empresa.STATUS_CHOICES,
        plano_trial_contexto=construir_contexto_trial_plano(getattr(empresa, "plano", None)),
    )

    return render(request, "plataforma/empresa_alterar_plano.html", context)


@login_required
@platform_admin_required
def toggle_empresa_ativa(request, pk):
    empresa = obter_empresa(pk)
    resultado = empresas_service.processar_fluxo_toggle_ativa_empresa(
        method=request.method,
        empresa=empresa,
    )
    if not resultado["ok"]:
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    messages.success(request, resultado["mensagem"])
    return redirect("plataforma:empresa_detail", pk=empresa.pk)


@login_required
@platform_admin_required
def atualizar_logo_empresa(request, pk):
    empresa = obter_empresa(pk)
    resultado = empresas_service.atualizar_logo_empresa(
        method=request.method,
        empresa=empresa,
        logo_file=request.FILES.get("logo"),
    )
    if not resultado.ok:
        if resultado.erro != "metodo_invalido":
            messages.error(request, resultado.erro)
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    messages.success(request, f"Logo da empresa '{empresa.nome}' atualizado com sucesso.")
    return redirect("plataforma:empresa_detail", pk=empresa.pk)


@login_required
@platform_admin_required
def remover_logo_empresa(request, pk):
    empresa = obter_empresa(pk)
    resultado = empresas_service.remover_logo_empresa(
        method=request.method,
        empresa=empresa,
    )
    if not resultado.ok:
        if resultado.erro != "metodo_invalido":
            messages.error(request, resultado.erro)
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    messages.success(request, f"Logo da empresa '{empresa.nome}' removido com sucesso.")
    return redirect("plataforma:empresa_detail", pk=empresa.pk)
