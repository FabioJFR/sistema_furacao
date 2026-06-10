from inspecao_ai.models import (
    AnaliseImagemAI,
    AnaliseZonaPresetAI,
    ChatMensagemAI,
    ChatSessaoAI,
    DeteccaoImagemAI,
    ExemploTreinoAI,
    MemoriaTrabalhoAI,
)


INSPECAO_AI_MODEL_MAP = {
    "AnaliseImagemAI": AnaliseImagemAI,
    "DeteccaoImagemAI": DeteccaoImagemAI,
    "ExemploTreinoAI": ExemploTreinoAI,
    "AnaliseZonaPresetAI": AnaliseZonaPresetAI,
    "MemoriaTrabalhoAI": MemoriaTrabalhoAI,
    "ChatSessaoAI": ChatSessaoAI,
    "ChatMensagemAI": ChatMensagemAI,
}
