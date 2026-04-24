# plataforma/views/planos.py
# plataforma/views/planos.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

from plataforma.decorators import platform_admin_required
from plataforma.forms.plano import PlanoForm
from plataforma.selectors.planos import listar_planos_dashboard, obter_plano_por_pk
from plataforma.services.planos import alternar_plano_ativo

# TODO futuro:
# - aplicar services layer para gestão de planos
# - separar lógica de negócio (criação/edição) das views
# - validar impacto de alterações de plano em empresas ativas


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
    if request.method == "POST":
        form = PlanoForm(request.POST)
        if form.is_valid():
            plano = form.save()

            messages.success(request, f"Plano '{plano.nome}' criado com sucesso.")
            return redirect("plataforma:plano_list")

        messages.error(request, "Erro ao criar plano. Verifique os dados.")
    else:
        form = PlanoForm()

    return render(request, "plataforma/plano_form.html", {
        "form": form,
        "titulo": "Novo Plano",
    })


# ---------------- EDITAR PLANO ----------------
@login_required
@platform_admin_required
def plano_update(request, pk):
    plano = obter_plano_por_pk(pk)

    if request.method == "POST":
        form = PlanoForm(request.POST, instance=plano)
        if form.is_valid():
            plano = form.save()

            messages.success(request, "Plano atualizado com sucesso.")
            return redirect("plataforma:plano_list")

        messages.error(request, "Erro ao atualizar plano.")
    else:
        form = PlanoForm(instance=plano)

    return render(request, "plataforma/plano_form.html", {
        "form": form,
        "titulo": f"Editar Plano - {plano.nome}",
        "plano": plano,
    })


# ---------------- ATIVAR/DESATIVAR PLANO ----------------
@login_required
@platform_admin_required
def plano_toggle_ativo(request, pk):
    plano = obter_plano_por_pk(pk)
    plano = alternar_plano_ativo(plano)

    messages.success(request, f"Plano '{plano.nome}' atualizado.")
    return redirect("plataforma:plano_list")


# ---------------- TODO FUTURO ----------------
# - ligar planos a subscrições (SubscricaoEmpresa)
# - impedir edição de planos em uso ativo (ou criar versãoing de planos)
# - adicionar histórico de alterações de preço
# - adicionar integração com pagamentos (Stripe / PayPal)
# - adicionar métricas por plano (quantas empresas usam cada plano)
