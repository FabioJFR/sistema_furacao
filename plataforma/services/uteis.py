import json
from io import StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

from plataforma.selectors.uteis import AI_DELETE_MODELS_BY_GROUP


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
