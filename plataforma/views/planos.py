# plataforma/views/planos.py
# plataforma/views/planos.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext as _

from plataforma.decorators import platform_admin_required
from plataforma.selectors.planos import listar_planos_dashboard, obter_plano_por_pk
from plataforma.services.planos import (
    alternar_plano_ativo,
    processar_fluxo_form_plano,
)


# ---------------- LISTAR PLANOS ----------------
@login_required
@platform_admin_required
def plano_list(request):
    planos = listar_planos_dashboard()

    context = {
        "planos": planos,
        "planos_ativos": planos.filter(ativo=True).count(),
        "planos_empresa": planos.filter(tipo="empresa").count(),
        "planos_individuais": planos.filter(tipo="individual").count(),
    }

    return render(request, "plataforma/plano_list.html", context)


# ---------------- CRIAR PLANO ----------------
@login_required
@platform_admin_required
def plano_create(request):
    fluxo = processar_fluxo_form_plano(
        method=request.method,
        post_data=request.POST,
        plano=None,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            messages.success(request, resultado["mensagem"])
            return redirect("plataforma:plano_list")
        messages.error(request, resultado["mensagem"])

    return render(request, "plataforma/plano_form.html", {
        "form": form,
        "titulo": _("Novo Plano"),
    })


# ---------------- EDITAR PLANO ----------------
@login_required
@platform_admin_required
def plano_update(request, pk):
    plano = obter_plano_por_pk(pk)

    fluxo = processar_fluxo_form_plano(
        method=request.method,
        post_data=request.POST,
        plano=plano,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        if resultado["ok"]:
            plano = resultado["plano"]
            messages.success(request, resultado["mensagem"])
            return redirect("plataforma:plano_list")
        messages.error(request, resultado["mensagem"])

    return render(request, "plataforma/plano_form.html", {
        "form": form,
        "titulo": _("Editar Plano - %(nome)s") % {"nome": plano.nome},
        "plano": plano,
    })


# ---------------- ATIVAR/DESATIVAR PLANO ----------------
@login_required
@platform_admin_required
def plano_toggle_ativo(request, pk):
    plano = obter_plano_por_pk(pk)
    plano = alternar_plano_ativo(plano)

    messages.success(request, _("Plano '%(nome)s' atualizado.") % {"nome": plano.nome})
    return redirect("plataforma:plano_list")


# ---------------- TODO FUTURO ----------------
# - ligar planos a subscrições (SubscricaoEmpresa)
# - impedir edição de planos em uso ativo (ou criar versãoing de planos)
# - adicionar histórico de alterações de preço
# - adicionar integração com pagamentos (Stripe / PayPal)
# - adicionar métricas por plano (quantas empresas usam cada plano)
