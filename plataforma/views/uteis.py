import json
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from plataforma.selectors.uteis import (
    construir_datasets_configurados_ai,
    construir_exports_ai_com_counts,
    construir_payload_exportacao_ai,
    obter_chaves_scope_exportacao,
    obter_counts_datasets_ai,
)
from plataforma.services.uteis import (
    construir_zip_exportacao_ai,
    executar_preenchimento_furos_materiais,
    limpar_dados_ai_por_scope,
)


def _superuser_only(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_superuser:
        messages.error(request, "Esta área está reservada ao superutilizador.")
        return redirect("projetos:redirect_after_login")
    return None


def _json_download_response(payload, filename):
    response = HttpResponse(
        json.dumps(payload, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
@login_required
def uteis_dashboard(request):
    acesso = _superuser_only(request)
    if acesso:
        return acesso

    if request.method == "POST" and request.POST.get("action") == "preencher_furos_materiais":
        empresa_param = (request.POST.get("empresa") or "").strip()
        raio_metros = (request.POST.get("raio_metros") or "250").strip()
        forcar_furos = request.POST.get("forcar_furos") == "on"
        simular = request.POST.get("simular") == "on"

        try:
            saida_seed = executar_preenchimento_furos_materiais(
                empresa_param=empresa_param,
                raio_metros=raio_metros,
                forcar_furos=forcar_furos,
                simular=simular,
            )
            if simular:
                messages.success(
                    request,
                    "Simulação executada com sucesso. Nenhum dado foi gravado.",
                )
            else:
                messages.success(
                    request,
                    "Preenchimento de coordenadas e reforço de materiais executado com sucesso.",
                )
        except Exception as exc:
            messages.error(
                request,
                f"Erro ao executar o reforço de furos e materiais: {exc}",
            )
            saida_seed = ""
        request.session["uteis_last_seed_output"] = saida_seed
        request.session["uteis_last_seed_options"] = {
            "empresa": empresa_param,
            "raio_metros": raio_metros or "250",
            "forcar_furos": forcar_furos,
            "simular": simular,
        }
        return redirect("plataforma:uteis_dashboard")

    counts_by_key = obter_counts_datasets_ai()
    exports = construir_exports_ai_com_counts(counts_by_key)
    context = {
        "exports": exports,
        "datasets_configurados": construir_datasets_configurados_ai(counts_by_key),
        "seed_form_initial": request.session.get(
            "uteis_last_seed_options",
            {"empresa": "", "raio_metros": "250", "forcar_furos": False, "simular": False},
        ),
        "seed_last_output": request.session.get("uteis_last_seed_output", ""),
    }
    return render(request, "plataforma/uteis_dashboard.html", context)


@login_required
def uteis_export_ai_json(request, scope):
    acesso = _superuser_only(request)
    if acesso:
        return acesso

    payload = construir_payload_exportacao_ai()
    generated_date = timezone.now().strftime("%Y%m%d_%H%M%S")

    scoped_keys = obter_chaves_scope_exportacao(scope)

    if scoped_keys:
        return _json_download_response(
            {
                "generated_at": payload["generated_at"],
                "datasets": {key: payload["datasets"][key] for key in scoped_keys},
            },
            f"ai_{scope}_{generated_date}.json",
        )

    if scope == "full":
        buffer = BytesIO()
        construir_zip_exportacao_ai(payload=payload, archive_file=buffer)
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="ai_database_export_{generated_date}.zip"'
        return response

    messages.error(request, "Exportação AI não reconhecida.")
    return redirect("plataforma:uteis_dashboard")


@login_required
def uteis_clear_scope(request, scope):
    acesso = _superuser_only(request)
    if acesso:
        return acesso

    if request.method != "POST":
        messages.error(request, "A limpeza de dados exige confirmação por formulário.")
        return redirect("plataforma:uteis_dashboard")

    deleted_total, reconhecido = limpar_dados_ai_por_scope(scope)
    if not reconhecido:
        messages.error(request, "Grupo de limpeza não reconhecido.")
        return redirect("plataforma:uteis_dashboard")

    messages.success(request, f"Foram limpos os dados do grupo '{scope}' ({deleted_total} registos contabilizados).")
    return redirect("plataforma:uteis_dashboard")
