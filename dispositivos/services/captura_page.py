from django.db import ProgrammingError

from dispositivos.selectors.importacao_historico import listar_historico_importacoes_qs
from dispositivos.services.dashboard_capture import processar_criacao_sessao_captura
from dispositivos.services.dashboard_import import processar_acao_importacao_magcruiser
from dispositivos.services.serial_service import capturar_leitura_serial_para_sessao


def listar_historico_importacoes_seguro(*, empresa_id):
    try:
        historico = list(
            listar_historico_importacoes_qs(empresa_id=empresa_id).order_by("-criado_em")[:20]
        )
        return {"historico": historico, "mensagem_warning": None}
    except ProgrammingError:
        return {
            "historico": [],
            "mensagem_warning": (
                "Histórico de importações ainda não disponível nesta base de dados. "
                "Aplica as migrations da app Dispositivos."
            ),
        }


def processar_post_captura_dispositivo(
    *,
    action,
    empresa_id,
    empregado,
    request_post,
    request_files,
    request_session,
    utilizador,
    preview_session_key,
    report_session_key,
):
    if action in {"preview_import", "save_import", "clear_import", "clear_import_report"}:
        try:
            resultado_acao = processar_acao_importacao_magcruiser(
                action=action,
                empresa_id=empresa_id,
                request_post=request_post,
                request_files=request_files,
                request_session=request_session,
                utilizador=utilizador,
                preview_session_key=preview_session_key,
                report_session_key=report_session_key,
            )
            return {
                "redirect_name": "dispositivos:captura",
                "redirect_kwargs": {},
                "message_level": resultado_acao.get("message_level"),
                "message": resultado_acao.get("message"),
            }
        except Exception as exc:
            return {
                "redirect_name": "dispositivos:captura",
                "redirect_kwargs": {},
                "message_level": "error",
                "message": f"Erro na ação de importação: {exc}",
            }

    resultado = processar_criacao_sessao_captura(
        empresa_id=empresa_id,
        empregado=empregado,
        dispositivo_id=request_post.get("dispositivo_id"),
        furo_id=request_post.get("furo_id"),
    )
    if not resultado["ok"]:
        return {
            "redirect_name": "dispositivos:captura",
            "redirect_kwargs": {},
            "message_level": "error",
            "message": resultado["erro"],
        }

    sessao = resultado["sessao"]
    return {
        "redirect_name": "dispositivos:sessao_detail",
        "redirect_kwargs": {"pk": sessao.pk},
        "message_level": "success",
        "message": "Sessão criada com sucesso.",
    }


def processar_captura_leitura_serial_sessao(*, sessao):
    try:
        leitura = capturar_leitura_serial_para_sessao(sessao)
        return {
            "ok": True,
            "message_level": "success",
            "message": f"Leitura bruta capturada com sucesso. Sequência: {leitura.sequencia}",
        }
    except Exception as exc:
        return {
            "ok": False,
            "message_level": "error",
            "message": f"Erro ao capturar leitura serial: {exc}",
        }
