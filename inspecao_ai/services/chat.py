from inspecao_ai.models import ChatMensagemAI, ChatSessaoAI


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
