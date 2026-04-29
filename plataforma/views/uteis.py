from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from plataforma.services.uteis import (
    construir_contexto_dashboard_uteis,
    construir_resposta_download_json,
    construir_resposta_download_zip,
    garantir_acesso_superuser,
    processar_limpeza_scope,
    processar_scope_exportacao,
    processar_submit_preenchimento_dashboard,
)


@login_required
def uteis_dashboard(request):
    acesso = garantir_acesso_superuser(request)
    if acesso:
        return acesso

    if request.method == "POST" and request.POST.get("action") == "preencher_furos_materiais":
        resultado = processar_submit_preenchimento_dashboard(request.POST)
        if resultado["ok"]:
            messages.success(request, resultado["mensagem_sucesso"])
        else:
            messages.error(request, resultado["mensagem_erro"])
        request.session["uteis_last_seed_output"] = resultado["saida_seed"]
        request.session["uteis_last_seed_options"] = resultado["opcoes"]
        return redirect("plataforma:uteis_dashboard")

    context = construir_contexto_dashboard_uteis(request.session)
    return render(request, "plataforma/uteis_dashboard.html", context)


@login_required
def uteis_export_ai_json(request, scope):
    acesso = garantir_acesso_superuser(request)
    if acesso:
        return acesso

    resultado = processar_scope_exportacao(scope)
    if not resultado["ok"]:
        messages.error(request, resultado["mensagem"])
        return redirect("plataforma:uteis_dashboard")
    if resultado["tipo"] == "json":
        return construir_resposta_download_json(
            resultado["payload"],
            resultado["filename"],
        )
    if resultado["tipo"] == "zip":
        return construir_resposta_download_zip(
            payload=resultado["payload"],
            generated_date=resultado["generated_date"],
        )
    messages.error(request, "Exportação AI não reconhecida.")
    return redirect("plataforma:uteis_dashboard")


@login_required
def uteis_clear_scope(request, scope):
    acesso = garantir_acesso_superuser(request)
    if acesso:
        return acesso

    resultado = processar_limpeza_scope(method=request.method, scope=scope)
    if resultado["ok"]:
        messages.success(request, resultado["mensagem"])
    else:
        messages.error(request, resultado["mensagem"])
    return redirect("plataforma:uteis_dashboard")
