from inspecao_ai.models import ChatMensagemAI, ChatSessaoAI
from inspecao_ai.chat_services import (
    construir_resumo_empresa,
    gerar_resposta_chat,
    normalizar_json_chat,
)
from inspecao_ai import domain_logic as dl
from inspecao_ai.selectors.chat import listar_sessoes_chat_ativas_empresa, obter_sessao_chat_empresa


def criar_sessao_chat(*, empresa, utilizador, pergunta):
    return ChatSessaoAI.objects.create(
        empresa=empresa,
        utilizador=utilizador,
        titulo=(pergunta[:80] or "Nova conversa AI"),
    )


def criar_mensagem_chat(*, sessao, papel, conteudo, metadados=None):
    payload = {
        "sessao": sessao,
        "papel": papel,
        "conteudo": conteudo,
    }
    if metadados is not None:
        payload["metadados"] = metadados
    return ChatMensagemAI.objects.create(**payload)


def processar_interacao_chat(*, empresa, utilizador, sessao, pergunta, furo_contexto=None):
    pergunta = (pergunta or "").strip()

    if not sessao:
        sessao = criar_sessao_chat(empresa=empresa, utilizador=utilizador, pergunta=pergunta)

    if not pergunta:
        return sessao

    criar_mensagem_chat(sessao=sessao, papel="user", conteudo=pergunta)
    resposta, metadados = gerar_resposta_chat(empresa=empresa, pergunta=pergunta)
    criar_mensagem_chat(
        sessao=sessao,
        papel="assistant",
        conteudo=resposta,
        metadados=normalizar_json_chat(metadados),
    )

    if sessao.titulo == "Nova conversa AI":
        sessao.titulo = pergunta[:80]

    resumo_contexto = construir_resumo_empresa(empresa)
    if furo_contexto:
        resumo_contexto["memoria_furo_contexto"] = dl.construir_memoria_operacional_furo(furo_contexto)
    sessao.ultimo_resumo_contexto = normalizar_json_chat(resumo_contexto)
    sessao.save(update_fields=["titulo", "ultimo_resumo_contexto", "atualizado_em"])
    return sessao


def obter_sessao_e_lista_chatbox(*, empresa, sessao_id):
    sessoes = listar_sessoes_chat_ativas_empresa(empresa=empresa, limit=12)
    if sessao_id:
        sessao = obter_sessao_chat_empresa(sessao_id=sessao_id, empresa=empresa)
    else:
        sessao = sessoes[0] if sessoes else None
    return sessao, sessoes


def obter_memoria_furo_contexto_sessao(sessao):
    if not sessao or not sessao.ultimo_resumo_contexto:
        return None
    return sessao.ultimo_resumo_contexto.get("memoria_furo_contexto")
