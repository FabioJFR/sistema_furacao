from dispositivos.selectors.dashboard import obter_sessao_detail
from dispositivos.services.importacao_historico import criar_historico_importacao
from dispositivos.services.magcruiser_import import (
    gravar_importacao_magcruiser,
    parse_magcruiser_file,
)
from django.core.files.uploadedfile import SimpleUploadedFile
from projetos.models import Furo


def processar_preview_importacao_magcruiser(*, empresa_id, sessao_id, ficheiro):
    sessao = obter_sessao_detail(pk=sessao_id, empresa_id=empresa_id)
    resultado = parse_magcruiser_file(ficheiro)

    nomes_furo_detetados = sorted(
        {str(row.get("hole_name", "")).strip() for row in resultado["rows"] if row.get("hole_name")}
    )
    furos_existentes = {
        nome
        for nome in Furo.objects.filter(
            empresa_id=sessao.empresa_id,
            nome__in=nomes_furo_detetados,
        ).values_list("nome", flat=True)
    }
    furos_em_falta = [nome for nome in nomes_furo_detetados if nome not in furos_existentes]

    preview_data = {
        "sessao_id": str(sessao.pk),
        "filename": resultado["filename"],
        "formato": resultado["formato"],
        "total_linhas": resultado["total_linhas"],
        "nomes_furo_detetados": nomes_furo_detetados,
        "furos_existentes": sorted(furos_existentes),
        "furos_em_falta": furos_em_falta,
        "preview_rows": [
            {k: str(v) if v is not None else "" for k, v in row.items()}
            for row in resultado["preview_rows"]
        ],
        "rows": [
            {k: str(v) if v is not None else "" for k, v in row.items()}
            for row in resultado["rows"]
        ],
    }
    return preview_data


def processar_preview_importacao_magcruiser_texto(*, empresa_id, sessao_id, payload_texto, nome_ficheiro):
    nome = (nome_ficheiro or "").strip() or "webbluetooth_import.csv"
    texto = payload_texto or ""
    if not texto.strip():
        raise ValueError("Sem dados para importar do Web Bluetooth.")

    ficheiro = SimpleUploadedFile(
        name=nome,
        content=texto.encode("utf-8"),
        content_type="text/plain",
    )
    return processar_preview_importacao_magcruiser(
        empresa_id=empresa_id,
        sessao_id=sessao_id,
        ficheiro=ficheiro,
    )


def processar_gravacao_importacao_magcruiser(
    *,
    empresa_id,
    preview_guardado,
    modo_aplicacao,
    utilizador,
):
    sessao = obter_sessao_detail(pk=preview_guardado.get("sessao_id"), empresa_id=empresa_id)
    rows = [
        {
            "depth": row.get("depth"),
            "inc": row.get("inc"),
            "azi": row.get("azi"),
            "mag": row.get("mag") or None,
            "temp": row.get("temp") or None,
            "hole_name": row.get("hole_name") or None,
        }
        for row in preview_guardado.get("rows", [])
    ]

    resultado = gravar_importacao_magcruiser(
        sessao=sessao,
        rows=rows,
        modo_aplicacao=modo_aplicacao,
    )
    report_data = {
        "sessao_id": str(sessao.pk),
        "modo_aplicacao": modo_aplicacao,
        "total_gravadas": resultado.get("total_gravadas", 0),
        "total_ignoradas": resultado.get("total_ignoradas", 0),
        "furos_criados": resultado.get("furos_criados", 0),
        "furos_sem_match": resultado.get("furos_sem_match", []),
        "sugestoes_furos_sem_match": resultado.get("sugestoes_furos_sem_match", []),
        "resumo_por_furo": resultado.get("resumo_por_furo", {}),
    }

    criar_historico_importacao(
        empresa=sessao.empresa,
        sessao=sessao,
        utilizador=utilizador,
        nome_ficheiro=preview_guardado.get("filename"),
        formato=preview_guardado.get("formato"),
        modo_aplicacao=modo_aplicacao,
        total_linhas=len(rows),
        total_gravadas=resultado.get("total_gravadas", 0),
        total_ignoradas=resultado.get("total_ignoradas", 0),
        furos_criados=resultado.get("furos_criados", 0),
        furos_sem_match=resultado.get("furos_sem_match", []),
        resumo_por_furo=resultado.get("resumo_por_furo", {}),
    )

    return resultado, report_data


def processar_acao_importacao_magcruiser(
    *,
    action,
    empresa_id,
    request_post,
    request_files,
    request_session,
    utilizador,
    preview_session_key,
    report_session_key,
):
    action = (action or "").strip()

    if action == "preview_import":
        sessao_id = request_post.get("sessao_importacao_id")
        ficheiro = request_files.get("magcruiser_file")
        preview_data = processar_preview_importacao_magcruiser(
            empresa_id=empresa_id,
            sessao_id=sessao_id,
            ficheiro=ficheiro,
        )
        request_session[preview_session_key] = preview_data
        request_session.modified = True
        return {
            "handled": True,
            "message_level": "success",
            "message": (
                "Pré-visualização carregada: "
                f"{preview_data['total_linhas']} linhas do ficheiro {preview_data['filename']}."
            ),
        }

    if action == "save_import":
        preview_guardado = request_session.get(preview_session_key)
        if not preview_guardado:
            return {
                "handled": True,
                "message_level": "error",
                "message": "Não existe pré-visualização para gravar. Faça primeiro a pré-visualização.",
            }

        modo_aplicacao = (request_post.get("modo_aplicacao") or "all_existing").strip()
        resultado, report_data = processar_gravacao_importacao_magcruiser(
            empresa_id=empresa_id,
            preview_guardado=preview_guardado,
            modo_aplicacao=modo_aplicacao,
            utilizador=utilizador,
        )
        missing = resultado.get("furos_sem_match", [])
        missing_txt = f" Furos sem correspondência: {', '.join(missing)}." if missing else ""
        request_session[report_session_key] = report_data
        request_session.pop(preview_session_key, None)
        request_session.modified = True
        return {
            "handled": True,
            "message_level": "success",
            "message": (
                f"Foram gravadas {resultado['total_gravadas']} medições. "
                f"Ignoradas: {resultado.get('total_ignoradas', 0)}. "
                f"Furos criados: {resultado.get('furos_criados', 0)}."
                f"{missing_txt}"
            ),
        }

    if action == "clear_import":
        request_session.pop(preview_session_key, None)
        request_session.modified = True
        return {
            "handled": True,
            "message_level": "info",
            "message": "Pré-visualização removida.",
        }

    if action == "clear_import_report":
        request_session.pop(report_session_key, None)
        request_session.modified = True
        return {
            "handled": True,
            "message_level": "info",
            "message": "Relatório de importação removido.",
        }

    return {"handled": False}
