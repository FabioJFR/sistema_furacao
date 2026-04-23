import json
from io import BytesIO
from io import StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from inspecao_ai.models import (
    AnaliseImagemAI,
    AnaliseZonaPresetAI,
    ChatMensagemAI,
    ChatSessaoAI,
    DeteccaoImagemAI,
    MemoriaTrabalhoAI,
)
from projetos.models import Despesa, Furo, Medicao, Projeto, RegistoDiarioEmpregado, RegistoDiarioFotoAmostra


AI_EXPORT_DATASETS = [
    {
        "key": "analises_ai",
        "label": "Análises AI",
        "description": "Análises, metadados, campos extraídos e estado de revisão.",
        "model": AnaliseImagemAI,
        "group": "analises",
    },
    {
        "key": "deteccoes_ai",
        "label": "Deteções AI",
        "description": "Caixas delimitadoras, textos sugeridos e metadados das deteções.",
        "model": DeteccaoImagemAI,
        "group": "deteccoes",
    },
    {
        "key": "presets_zonas_ai",
        "label": "Presets de zonas AI",
        "description": "Presets reutilizáveis para orientar a leitura da AI.",
        "model": AnaliseZonaPresetAI,
        "group": "presets",
    },
    {
        "key": "memorias_trabalho_ai",
        "label": "Memórias de trabalho AI",
        "description": "Notas persistentes de continuidade e standby da AI.",
        "model": MemoriaTrabalhoAI,
        "group": "presets",
    },
    {
        "key": "chat_sessoes_ai",
        "label": "Sessões Chatbox AI",
        "description": "Sessões da AI conversacional.",
        "model": ChatSessaoAI,
        "group": "chat",
    },
    {
        "key": "chat_mensagens_ai",
        "label": "Mensagens Chatbox AI",
        "description": "Mensagens e contexto do chat AI.",
        "model": ChatMensagemAI,
        "group": "chat",
    },
    {
        "key": "projetos_operacionais",
        "label": "Projetos",
        "description": "Projetos operacionais da plataforma.",
        "model": Projeto,
        "group": "operacao",
    },
    {
        "key": "furos_operacionais",
        "label": "Furos",
        "description": "Furos e respetivo contexto operacional.",
        "model": Furo,
        "group": "operacao",
    },
    {
        "key": "medicoes_operacionais",
        "label": "Medições",
        "description": "Medições associadas aos furos.",
        "model": Medicao,
        "group": "operacao",
    },
    {
        "key": "registos_operacionais",
        "label": "Registos diários",
        "description": "Registos diários dos trabalhadores ligados à operação.",
        "model": RegistoDiarioEmpregado,
        "group": "operacao",
    },
    {
        "key": "registos_fotos_amostra",
        "label": "Fotos de amostra",
        "description": "Fotos de amostra associadas aos registos diários.",
        "model": RegistoDiarioFotoAmostra,
        "group": "operacao",
    },
    {
        "key": "despesas_operacionais",
        "label": "Despesas",
        "description": "Despesas ligadas a empresa, projeto, furo e operação.",
        "model": Despesa,
        "group": "operacao",
    },
]

AI_EXPORT_GROUPS = [
    {
        "slug": "analises",
        "label": "Análises AI",
        "description": "Analises, metadados, campos extraídos e estado de revisão.",
    },
    {
        "slug": "deteccoes",
        "label": "Deteções AI",
        "description": "Caixas delimitadoras, textos sugeridos e metadados das deteções.",
    },
    {
        "slug": "presets",
        "label": "Presets e memória AI",
        "description": "Presets de zonas reutilizáveis e memórias de trabalho guardadas.",
    },
    {
        "slug": "chat",
        "label": "Chatbox AI",
        "description": "Sessões e mensagens da AI conversacional.",
    },
    {
        "slug": "operacao",
        "label": "Projetos, furos e operação",
        "description": "Base operacional para memória futura da AI sobre zonas, furos, registos, medições e despesas.",
    },
]

AI_DELETE_MODELS_BY_GROUP = {
    "analises": [DeteccaoImagemAI, AnaliseImagemAI],
    "deteccoes": [DeteccaoImagemAI],
    "presets": [AnaliseZonaPresetAI, MemoriaTrabalhoAI],
    "chat": [ChatMensagemAI, ChatSessaoAI],
    "operacao": [RegistoDiarioFotoAmostra, Medicao, RegistoDiarioEmpregado, Despesa, Furo, Projeto],
    "full": [
        RegistoDiarioFotoAmostra,
        Medicao,
        RegistoDiarioEmpregado,
        Despesa,
        Furo,
        Projeto,
        ChatMensagemAI,
        ChatSessaoAI,
        AnaliseZonaPresetAI,
        MemoriaTrabalhoAI,
        DeteccaoImagemAI,
        AnaliseImagemAI,
    ],
}


def _superuser_only(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_superuser:
        messages.error(request, "Esta área está reservada ao superutilizador.")
        return redirect("projetos:redirect_after_login")
    return None


def _serialize_queryset(queryset):
    return list(queryset.values())


def _json_download_response(payload, filename):
    response = HttpResponse(
        json.dumps(payload, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _ai_export_payload():
    generated_at = timezone.now()
    datasets = {item["key"]: _serialize_queryset(item["model"].objects.all()) for item in AI_EXPORT_DATASETS}
    return {
        "generated_at": generated_at,
        "project": "sistema_furacao",
        "scope": "inspecao_ai",
        "datasets": datasets,
    }


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

        stdout_buffer = StringIO()
        call_kwargs = {
            "stdout": stdout_buffer,
            "raio_metros": raio_metros or "250",
            "forcar_furos": forcar_furos,
            "simular": simular,
        }
        if empresa_param:
            call_kwargs["empresa"] = empresa_param

        try:
            call_command("preencher_furos_e_materiais_base", **call_kwargs)
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
        request.session["uteis_last_seed_output"] = stdout_buffer.getvalue()
        request.session["uteis_last_seed_options"] = {
            "empresa": empresa_param,
            "raio_metros": raio_metros or "250",
            "forcar_furos": forcar_furos,
            "simular": simular,
        }
        return redirect("plataforma:uteis_dashboard")

    counts_by_key = {item["key"]: item["model"].objects.count() for item in AI_EXPORT_DATASETS}
    exports = []
    for group in AI_EXPORT_GROUPS:
        group_keys = [item["key"] for item in AI_EXPORT_DATASETS if item["group"] == group["slug"]]
        exports.append(
            {
                "slug": group["slug"],
                "label": group["label"],
                "description": group["description"],
                "count": sum(counts_by_key[key] for key in group_keys),
            }
        )
    context = {
        "exports": exports
        + [
            {
                "slug": "full",
                "label": "Pacote completo ZIP",
                "description": "Exportação completa das bases de dados da AI num único pacote.",
                "count": None,
            },
        ],
        "datasets_configurados": [
            {
                "key": item["key"],
                "label": item["label"],
                "description": item["description"],
                "group": item["group"],
                "count": counts_by_key[item["key"]],
            }
            for item in AI_EXPORT_DATASETS
        ],
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

    payload = _ai_export_payload()
    generated_date = timezone.now().strftime("%Y%m%d_%H%M%S")

    scoped_keys = [item["key"] for item in AI_EXPORT_DATASETS if item["group"] == scope]

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
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "generated_at": payload["generated_at"],
                        "project": payload["project"],
                        "scope": payload["scope"],
                        "datasets": list(payload["datasets"].keys()),
                    },
                    ensure_ascii=False,
                    indent=2,
                    cls=DjangoJSONEncoder,
                ),
            )
            for dataset_name, rows in payload["datasets"].items():
                archive.writestr(
                    f"{dataset_name}.json",
                    json.dumps(rows, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder),
                )
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

    models_to_clear = AI_DELETE_MODELS_BY_GROUP.get(scope)
    if not models_to_clear:
        messages.error(request, "Grupo de limpeza não reconhecido.")
        return redirect("plataforma:uteis_dashboard")

    deleted_total = 0
    with transaction.atomic():
        for model in models_to_clear:
            deleted_total += model.objects.count()
            model.objects.all().delete()

    messages.success(request, f"Foram limpos os dados do grupo '{scope}' ({deleted_total} registos contabilizados).")
    return redirect("plataforma:uteis_dashboard")
