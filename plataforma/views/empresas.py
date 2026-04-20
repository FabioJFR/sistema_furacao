from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

from plataforma.decorators import platform_admin_required
from plataforma.models import Empresa, Plano

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

    empresa = get_object_or_404(
        Empresa.objects.select_related("plano"),
        pk=pk,
    )

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
    }

    return render(request, "plataforma/empresa_detail.html", context)


@login_required
@platform_admin_required
def alterar_plano_empresa(request, pk):
    perfil = request.perfil_plataforma

    empresa = get_object_or_404(
        Empresa.objects.select_related("plano"),
        pk=pk,
    )

    planos = Plano.objects.filter(ativo=True).order_by("tipo", "preco_mensal", "nome")

    if request.method == "POST":
        plano_id = request.POST.get("plano")
        novo_plano = get_object_or_404(Plano, pk=plano_id, ativo=True)

        empresa.plano = novo_plano
        empresa.save(update_fields=["plano", "atualizado_em"])

        messages.success(
            request,
            f"Plano da empresa '{empresa.nome}' alterado para '{novo_plano.nome}' com sucesso.",
        )
        return redirect("plataforma:empresa_detail", pk=empresa.pk)

    context = {
        "empresa": empresa,
        "perfil": perfil,
        "planos": planos,
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