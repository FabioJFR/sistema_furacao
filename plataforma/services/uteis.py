import json
from io import StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib import messages
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from core.upload_security import diagnosticar_upload

from plataforma.selectors.uteis import (
    AI_DELETE_MODELS_BY_GROUP,
    construir_datasets_configurados_ai,
    construir_exports_ai_com_counts,
    construir_payload_exportacao_ai,
    obter_chaves_scope_exportacao,
    obter_counts_datasets_ai,
)


def normalizar_opcoes_preenchimento(*, empresa_param, raio_metros, forcar_furos, simular):
    return {
        "empresa": (empresa_param or "").strip(),
        "raio_metros": (raio_metros or "250").strip() or "250",
        "forcar_furos": bool(forcar_furos),
        "simular": bool(simular),
    }


def executar_preenchimento_furos_materiais(*, empresa_param, raio_metros, forcar_furos, simular):
    stdout_buffer = StringIO()
    call_kwargs = {
        "stdout": stdout_buffer,
        "raio_metros": raio_metros or "250",
        "forcar_furos": forcar_furos,
        "simular": simular,
    }
    if empresa_param:
        call_kwargs["empresa"] = empresa_param

    call_command("preencher_furos_e_materiais_base", **call_kwargs)
    return stdout_buffer.getvalue()


def executar_fluxo_preenchimento_furos_materiais(*, empresa_param, raio_metros, forcar_furos, simular):
    opcoes = normalizar_opcoes_preenchimento(
        empresa_param=empresa_param,
        raio_metros=raio_metros,
        forcar_furos=forcar_furos,
        simular=simular,
    )
    try:
        saida_seed = executar_preenchimento_furos_materiais(
            empresa_param=opcoes["empresa"],
            raio_metros=opcoes["raio_metros"],
            forcar_furos=opcoes["forcar_furos"],
            simular=opcoes["simular"],
        )
    except Exception as exc:
        return {
            "ok": False,
            "erro": str(exc),
            "saida_seed": "",
            "opcoes": opcoes,
        }
    return {
        "ok": True,
        "erro": "",
        "saida_seed": saida_seed,
        "opcoes": opcoes,
    }


def normalizar_opcoes_logs_geologicos(*, username, por_furo, dry_run, ignorar_existentes):
    return {
        "username": (username or "").strip() or "empregadogeologoteste",
        "por_furo": str((por_furo or "3")).strip() or "3",
        "dry_run": bool(dry_run),
        "ignorar_existentes": bool(ignorar_existentes),
    }


def executar_populacao_logs_geologicos(*, username, por_furo, dry_run, ignorar_existentes):
    stdout_buffer = StringIO()
    call_kwargs = {
        "stdout": stdout_buffer,
        "username": username,
        "por_furo": por_furo,
        "dry_run": dry_run,
        "ignorar_existentes": ignorar_existentes,
    }
    call_command("popular_logs_geologicos_empregado", **call_kwargs)
    return stdout_buffer.getvalue()


def executar_fluxo_populacao_logs_geologicos(*, username, por_furo, dry_run, ignorar_existentes):
    opcoes = normalizar_opcoes_logs_geologicos(
        username=username,
        por_furo=por_furo,
        dry_run=dry_run,
        ignorar_existentes=ignorar_existentes,
    )
    try:
        saida = executar_populacao_logs_geologicos(
            username=opcoes["username"],
            por_furo=opcoes["por_furo"],
            dry_run=opcoes["dry_run"],
            ignorar_existentes=opcoes["ignorar_existentes"],
        )
    except Exception as exc:
        return {
            "ok": False,
            "erro": str(exc),
            "saida": "",
            "opcoes": opcoes,
        }
    return {
        "ok": True,
        "erro": "",
        "saida": saida,
        "opcoes": opcoes,
    }


def construir_zip_exportacao_ai(*, payload, archive_file):
    with ZipFile(archive_file, "w", compression=ZIP_DEFLATED) as archive:
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


def limpar_dados_ai_por_scope(scope):
    models_to_clear = AI_DELETE_MODELS_BY_GROUP.get(scope)
    if not models_to_clear:
        return 0, False

    deleted_total = 0
    with transaction.atomic():
        for model in models_to_clear:
            deleted_total += model.objects.count()
            model.objects.all().delete()
    return deleted_total, True


def garantir_acesso_superuser(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_superuser:
        messages.error(request, "Esta área está reservada ao superutilizador.")
        return redirect("projetos:redirect_after_login")
    return None


def construir_resposta_download_json(payload, filename):
    response = HttpResponse(
        json.dumps(payload, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def construir_resposta_download_zip(*, payload, generated_date):
    from io import BytesIO

    buffer = BytesIO()
    construir_zip_exportacao_ai(payload=payload, archive_file=buffer)
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="ai_database_export_{generated_date}.zip"'
    return response


def processar_submit_preenchimento_dashboard(post_data):
    resultado = executar_fluxo_preenchimento_furos_materiais(
        empresa_param=post_data.get("empresa"),
        raio_metros=post_data.get("raio_metros"),
        forcar_furos=post_data.get("forcar_furos") == "on",
        simular=post_data.get("simular") == "on",
    )
    opcoes = resultado["opcoes"]
    saida_seed = resultado["saida_seed"]
    if resultado["ok"]:
        if opcoes["simular"]:
            mensagem = "Simulação executada com sucesso. Nenhum dado foi gravado."
        else:
            mensagem = "Preenchimento de coordenadas e reforço de materiais executado com sucesso."
        return {
            "ok": True,
            "mensagem_sucesso": mensagem,
            "mensagem_erro": "",
            "saida_seed": saida_seed,
            "opcoes": opcoes,
        }
    return {
        "ok": False,
        "mensagem_sucesso": "",
        "mensagem_erro": f"Erro ao executar o reforço de furos e materiais: {resultado['erro']}",
        "saida_seed": saida_seed,
        "opcoes": opcoes,
    }


def processar_submit_logs_geologicos_dashboard(post_data):
    resultado = executar_fluxo_populacao_logs_geologicos(
        username=post_data.get("username_geologo"),
        por_furo=post_data.get("por_furo_geologo"),
        dry_run=post_data.get("dry_run_geologo") == "on",
        ignorar_existentes=post_data.get("ignorar_existentes_geologo") == "on",
    )
    opcoes = resultado["opcoes"]
    saida = resultado["saida"]
    if resultado["ok"]:
        if opcoes["dry_run"]:
            mensagem = "Simulação de logs geológicos executada com sucesso."
        else:
            mensagem = "Preenchimento de logs geológicos executado com sucesso."
        return {
            "ok": True,
            "mensagem_sucesso": mensagem,
            "mensagem_erro": "",
            "saida_logs_geologicos": saida,
            "opcoes_logs_geologicos": opcoes,
            "saida_seed": "",
            "opcoes": None,
        }
    return {
        "ok": False,
        "mensagem_sucesso": "",
        "mensagem_erro": f"Erro ao executar preenchimento de logs geológicos: {resultado['erro']}",
        "saida_logs_geologicos": saida,
        "opcoes_logs_geologicos": opcoes,
        "saida_seed": "",
        "opcoes": None,
    }


def processar_fluxo_post_uteis_dashboard(*, method, post_data):
    if method != "POST":
        return {
            "handled": False,
            "ok": False,
            "resultado": None,
        }

    action = post_data.get("action")

    if action == "preencher_furos_materiais":
        resultado = processar_submit_preenchimento_dashboard(post_data)
        return {
            "handled": True,
            "ok": bool(resultado.get("ok")),
            "resultado": resultado,
        }

    if action == "popular_logs_geologicos":
        resultado = processar_submit_logs_geologicos_dashboard(post_data)
        return {
            "handled": True,
            "ok": bool(resultado.get("ok")),
            "resultado": resultado,
        }

    if action == "diagnostico_upload":
        return {
            "handled": True,
            "ok": False,
            "resultado": {
                "ok": False,
                "mensagem_sucesso": "",
                "mensagem_erro": "Pedido inválido para diagnóstico de upload.",
            },
        }

    if action != "preencher_furos_materiais":
        return {
            "handled": False,
            "ok": False,
            "resultado": None,
        }
    return {"handled": False, "ok": False, "resultado": None}


def processar_submit_diagnostico_upload(*, upload_file, tipo_esperado):
    if not upload_file:
        return {
            "ok": False,
            "mensagem_sucesso": "",
            "mensagem_erro": "Seleciona um ficheiro para diagnóstico.",
            "diagnostico": None,
            "opcoes": {"tipo_esperado": tipo_esperado or "auto"},
        }
    diagnostico = diagnosticar_upload(upload_file, tipo_esperado=tipo_esperado or "auto")
    if diagnostico["ok"]:
        return {
            "ok": True,
            "mensagem_sucesso": "Diagnóstico concluído: ficheiro válido para upload.",
            "mensagem_erro": "",
            "diagnostico": diagnostico,
            "opcoes": {"tipo_esperado": tipo_esperado or "auto"},
        }
    return {
        "ok": False,
        "mensagem_sucesso": "",
        "mensagem_erro": f"Diagnóstico falhou: {diagnostico.get('erro') or 'erro desconhecido'}",
        "diagnostico": diagnostico,
        "opcoes": {"tipo_esperado": tipo_esperado or "auto"},
    }


def construir_contexto_dashboard_uteis(session):
    counts_by_key = obter_counts_datasets_ai()
    return {
        "exports": construir_exports_ai_com_counts(counts_by_key),
        "datasets_configurados": construir_datasets_configurados_ai(counts_by_key),
        "seed_form_initial": session.get(
            "uteis_last_seed_options",
            {"empresa": "", "raio_metros": "250", "forcar_furos": False, "simular": False},
        ),
        "seed_last_output": session.get("uteis_last_seed_output", ""),
        "logs_geologicos_form_initial": session.get(
            "uteis_last_logs_geologicos_options",
            {
                "username": "empregadogeologoteste",
                "por_furo": "3",
                "dry_run": True,
                "ignorar_existentes": False,
            },
        ),
        "logs_geologicos_last_output": session.get("uteis_last_logs_geologicos_output", ""),
        "upload_diagnostico": session.get("uteis_upload_diagnostico"),
        "upload_diagnostico_opcoes": session.get(
            "uteis_upload_diagnostico_opcoes",
            {"tipo_esperado": "auto"},
        ),
    }


def processar_scope_exportacao(scope):
    payload = construir_payload_exportacao_ai()
    generated_date = timezone.now().strftime("%Y%m%d_%H%M%S")
    scoped_keys = obter_chaves_scope_exportacao(scope)
    if scoped_keys:
        return {
            "ok": True,
            "tipo": "json",
            "generated_date": generated_date,
            "payload": {
                "generated_at": payload["generated_at"],
                "datasets": {key: payload["datasets"][key] for key in scoped_keys},
            },
            "filename": f"ai_{scope}_{generated_date}.json",
        }
    if scope == "full":
        return {
            "ok": True,
            "tipo": "zip",
            "generated_date": generated_date,
            "payload": payload,
        }
    return {"ok": False, "tipo": "erro", "mensagem": "Exportação AI não reconhecida."}


def processar_limpeza_scope(*, method, scope):
    if method != "POST":
        return {"ok": False, "mensagem": "A limpeza de dados exige confirmação por formulário."}
    deleted_total, reconhecido = limpar_dados_ai_por_scope(scope)
    if not reconhecido:
        return {"ok": False, "mensagem": "Grupo de limpeza não reconhecido."}
    return {
        "ok": True,
        "mensagem": f"Foram limpos os dados do grupo '{scope}' ({deleted_total} registos contabilizados).",
    }
