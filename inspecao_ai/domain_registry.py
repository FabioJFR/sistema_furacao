from inspecao_ai.models import (
    AnaliseImagemAI,
    AnaliseZonaPresetAI,
    ChatMensagemAI,
    ChatSessaoAI,
    DeteccaoImagemAI,
    MemoriaTrabalhoAI,
)


INSPECAO_AI_MODEL_MAP = {
    "AnaliseImagemAI": AnaliseImagemAI,
    "DeteccaoImagemAI": DeteccaoImagemAI,
    "AnaliseZonaPresetAI": AnaliseZonaPresetAI,
    "MemoriaTrabalhoAI": MemoriaTrabalhoAI,
    "ChatSessaoAI": ChatSessaoAI,
    "ChatMensagemAI": ChatMensagemAI,
}

