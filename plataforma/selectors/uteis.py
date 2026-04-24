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


def serializar_queryset(queryset):
    return list(queryset.values())


def obter_counts_datasets_ai():
    return {item["key"]: item["model"].objects.count() for item in AI_EXPORT_DATASETS}


def construir_exports_ai_com_counts(counts_by_key):
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
    exports.append(
        {
            "slug": "full",
            "label": "Pacote completo ZIP",
            "description": "Exportação completa das bases de dados da AI num único pacote.",
            "count": None,
        }
    )
    return exports


def construir_datasets_configurados_ai(counts_by_key):
    return [
        {
            "key": item["key"],
            "label": item["label"],
            "description": item["description"],
            "group": item["group"],
            "count": counts_by_key[item["key"]],
        }
        for item in AI_EXPORT_DATASETS
    ]


def obter_chaves_scope_exportacao(scope):
    return [item["key"] for item in AI_EXPORT_DATASETS if item["group"] == scope]


def construir_payload_exportacao_ai():
    generated_at = timezone.now()
    datasets = {item["key"]: serializar_queryset(item["model"].objects.all()) for item in AI_EXPORT_DATASETS}
    return {
        "generated_at": generated_at,
        "project": "sistema_furacao",
        "scope": "inspecao_ai",
        "datasets": datasets,
    }

