from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from plataforma.models import Empresa
from plataforma.selectors.furo_arquivado import (
    listar_estados_arquivo_furos,
    listar_furos_arquivados_com_filtros,
    obter_furo_arquivado,
)
from plataforma.services.uteis import (
    construir_contexto_dashboard_uteis,
    construir_resposta_download_json,
    construir_resposta_download_zip,
    garantir_acesso_superuser,
    processar_fluxo_post_uteis_dashboard,
    processar_limpeza_scope,
    processar_scope_exportacao,
)


@login_required
def uteis_dashboard(request):
    acesso = garantir_acesso_superuser(request)
    if acesso:
        return acesso

    fluxo = processar_fluxo_post_uteis_dashboard(
        method=request.method,
        post_data=request.POST,
    )
    if fluxo["handled"]:
        resultado = fluxo["resultado"]
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


@login_required
def uteis_arquivo_furos(request):
    acesso = garantir_acesso_superuser(request)
    if acesso:
        return acesso

    empresa_id = (request.GET.get("empresa") or "").strip()
    nome_furo = (request.GET.get("nome_furo") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    page = request.GET.get("page") or 1

    registos_page = listar_furos_arquivados_com_filtros(
        empresa_id=empresa_id or None,
        nome_furo=nome_furo,
        estado=estado,
        page=page,
        per_page=20,
    )

    context = {
        "registos_page": registos_page,
        "empresas": Empresa.objects.order_by("nome"),
        "estados_arquivo": listar_estados_arquivo_furos(),
        "filtros": {
            "empresa": empresa_id,
            "nome_furo": nome_furo,
            "estado": estado,
        },
    }
    return render(request, "plataforma/uteis_arquivo_furos.html", context)


@login_required
def uteis_arquivo_furo_detail(request, pk):
    acesso = garantir_acesso_superuser(request)
    if acesso:
        return acesso

    registo = obter_furo_arquivado(pk)
    return render(
        request,
        "plataforma/uteis_arquivo_furo_detail.html",
        {"registo": registo},
    )
