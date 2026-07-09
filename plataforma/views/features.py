from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from plataforma.decorators import platform_admin_required
from plataforma.services.features import (
    processar_submissao_features_dashboard,
    resolver_contexto_features_dashboard,
)


@login_required
@platform_admin_required
def features_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, _("A gestão global de features está reservada ao superuser."))
        return redirect("plataforma:dashboard")

    tipo_alvo_param = (request.GET.get("tipo") or request.POST.get("tipo") or "empresa").strip()
    alvo_id_param = (request.GET.get("alvo") or request.POST.get("alvo") or "").strip()
    contexto = resolver_contexto_features_dashboard(
        tipo_param=tipo_alvo_param,
        alvo_param=alvo_id_param,
    )
    tipo_alvo = contexto["tipo_alvo"]
    alvo = contexto["alvo"]

    if request.method == "POST":
        resultado = processar_submissao_features_dashboard(
            post_data=request.POST,
            tipo_alvo=tipo_alvo,
            alvo=alvo,
        )
        if not resultado["ok"]:
            messages.error(request, resultado["mensagem_erro"])
            return redirect("plataforma:features_dashboard")

        messages.success(request, resultado["mensagem_sucesso"])
        return redirect(f"{request.path}{resultado['redirect_url']}")

    return render(request, "plataforma/features_dashboard.html", contexto)
