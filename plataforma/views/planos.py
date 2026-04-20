# plataforma/views/planos.py
# plataforma/views/planos.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from plataforma.decorators import platform_admin_required
from plataforma.models import Plano
from plataforma.forms.plano import PlanoForm

# TODO futuro:
# - aplicar services layer para gestão de planos
# - separar lógica de negócio (criação/edição) das views
# - validar impacto de alterações de plano em empresas ativas


# ---------------- LISTAR PLANOS ----------------
@login_required
@platform_admin_required
def plano_list(request):
    planos = Plano.objects.all().order_by("preco_mensal")

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
    plano = get_object_or_404(Plano, pk=pk)

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
    plano = get_object_or_404(Plano, pk=pk)

    plano.ativo = not plano.ativo
    plano.save()

    messages.success(request, f"Plano '{plano.nome}' atualizado.")
    return redirect("plataforma:plano_list")


# ---------------- TODO FUTURO ----------------
# - ligar planos a subscrições (SubscricaoEmpresa)
# - impedir edição de planos em uso ativo (ou criar versãoing de planos)
# - adicionar histórico de alterações de preço
# - adicionar integração com pagamentos (Stripe / PayPal)
# - adicionar métricas por plano (quantas empresas usam cada plano)