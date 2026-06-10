
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from plataforma.decorators import platform_admin_required
from plataforma.models import PerfilPlataforma
from plataforma.services.subscricoes import construir_contexto_subscricao_list
from website.services import reenviar_confirmacao_utilizador


# TODO futuro:
# - mover regras de filtros/ordenação para selectors próprios
# - criar detalhe da subscrição
# - permitir renovar/cancelar/reactivar subscrição
# - destacar subscrições expiradas e próximas do vencimento
# - ligar subscrições a pagamentos reais


@login_required
@platform_admin_required
def subscricao_list(request):
    return render(
        request,
        "plataforma/subscricao_list.html",
        construir_contexto_subscricao_list(perfil=request.perfil_plataforma),
    )


@login_required
@platform_admin_required
def reenviar_ativacao_conta_admin(request, perfil_id):
    if request.method != "POST":
        return redirect("plataforma:subscricao_list")

    if not request.user.is_superuser:
        messages.error(request, "O reenvio de ativação está reservado ao superuser.")
        return redirect("plataforma:subscricao_list")

    perfil = get_object_or_404(
        PerfilPlataforma.objects.select_related("user", "empresa"),
        pk=perfil_id,
        tipo_acesso="empresa_admin",
    )

    try:
        enviado = reenviar_confirmacao_utilizador(user=perfil.user, request=request)
    except Exception:
        messages.error(
            request,
            "Nao foi possivel reenviar o email de ativacao neste momento. Verifique a configuracao SMTP.",
        )
        return redirect("plataforma:subscricao_list")

    if not enviado:
        messages.info(
            request,
            "A conta selecionada ja esta ativada ou nao necessita de novo email de confirmacao.",
        )
    else:
        messages.success(
            request,
            f"Email de ativacao reenviado para {perfil.user.email or perfil.user.username}.",
        )
    return redirect("plataforma:subscricao_list")
