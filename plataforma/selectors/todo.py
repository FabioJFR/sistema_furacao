from django.http import Http404


_AREAS_TODO = {
    "plataforma": {
        "nome": "Plataforma",
        "descricao": "Backoffice SaaS, subscrições, features, finanças e operações de administração global.",
        "feito": [
            "Dashboard de plataforma com métricas operacionais e atalhos rápidos.",
            "Gestão de planos/subscrições com fluxo de cobrança e configuração PayPal.",
            "Controlo de features por entidade (empresa/individual) com painel dedicado.",
            "Área de úteis para exportação/limpeza de dados de IA e tarefas técnicas.",
        ],
        "proximos_passos": [
            "Consolidar mais regras em services/selectors para reduzir lógica residual nas views.",
            "Fechar ciclo de auditoria de permissões por tipo de conta com cenários automatizados.",
            "Expandir cobertura de internacionalização (conteúdos e mensagens de backend).",
        ],
        "falta_fazer": [
            "API versionada para operações administrativas críticas.",
            "Testes end-to-end de onboarding/subscrição/pagamento.",
        ],
        "estado_logica": "Boa evolução: já existe separação forte em selectors/services, mas ainda há pontos a consolidar.",
    },
    "dispositivos": {
        "nome": "Dispositivos",
        "descricao": "Integração e monitorização de equipamentos e telemetria operacional.",
        "feito": [
            "Dashboard e navegação principal de dispositivos disponível na plataforma.",
            "Estruturas para registo/consulta de leituras e integração operacional já em produção.",
        ],
        "proximos_passos": [
            "Uniformizar todos os fluxos de escrita em services (criação/edição/ações).",
            "Adicionar validações de consistência para entradas de telemetria em lote.",
        ],
        "falta_fazer": [
            "API pública para ingestão externa com autenticação forte e versionamento.",
            "Observabilidade detalhada por dispositivo (latência, erro, disponibilidade).",
        ],
        "estado_logica": "Intermédio: base funcional estável, mas ainda há espaço para mais isolamento da lógica.",
    },
    "projetos": {
        "nome": "Projetos",
        "descricao": "Gestão principal do negócio: projetos, furos, registos, materiais, medições e equipa.",
        "feito": [
            "Fluxos completos para projetos/furos/medições/materiais e operações de campo.",
            "Várias rotas já migradas para services/selectors (empregados, stock, acesso contextual, sugestões).",
            "Suporte a contas individual e empregado com regras específicas de acesso.",
        ],
        "proximos_passos": [
            "Continuar migração de lógica restante de views para camadas dedicadas.",
            "Unificar validações de domínio críticas (ex.: regras de inclinação por tipo de furo).",
            "Reforçar testes de regressão para permissões entre superuser/admin/empregado/individual.",
        ],
        "falta_fazer": [
            "API versionada para mobile/sensores/drones com contratos estáveis.",
            "Histórico temporal completo de evolução de furo com consultas otimizadas.",
        ],
        "estado_logica": "Boa, mas ainda com pontos a fechar: app em transição ativa para arquitetura service/selector.",
    },
    "ia": {
        "nome": "IA",
        "descricao": "AI Visual, chatbox operacional, memória de trabalho e biblioteca documental.",
        "feito": [
            "Hub IA, chatbox, memória operacional e histórico de análises disponíveis.",
            "Suporte a biblioteca de documentos para contexto operacional da IA.",
            "Exportação/limpeza de datasets IA disponível na área de úteis (superuser).",
        ],
        "proximos_passos": [
            "Aumentar qualidade de OCR e pipelines por zona configurável.",
            "Consolidar leitura multimodal e pós-processamento semântico por domínio.",
            "Estruturar serviços de resposta guiada com sugestões clicáveis em mais cenários.",
        ],
        "falta_fazer": [
            "RAG/API versionada com controles de permissão por empresa/projeto.",
            "Métricas de qualidade por tipo de documento e feedback loop contínuo.",
        ],
        "estado_logica": "Intermédio: núcleo já funcional, com refatoração contínua para serviços especializados.",
    },
    "geologia": {
        "nome": "Geologia",
        "descricao": "Operação geológica, integração drone e suporte técnico de terreno.",
        "feito": [
            "Hub geologia e interfaces de drone integrados no ecossistema principal.",
            "Refatorações recentes já moveram partes de submissão para services dedicados.",
        ],
        "proximos_passos": [
            "Migrar restantes ações de escrita e importação para services/selectors.",
            "Padronizar validações de missão e trilhas de auditoria operacionais.",
        ],
        "falta_fazer": [
            "API de operações em tempo real com autenticação por dispositivo/operador.",
            "Pipeline de dados espaciais para analytics preditivo.",
        ],
        "estado_logica": "Intermédio: melhorou, mas ainda existem áreas com lógica a consolidar.",
    },
    "website": {
        "nome": "Website",
        "descricao": "Site público, páginas de entrada e jornada comercial/branding.",
        "feito": [
            "Homepage e estrutura pública funcional em produção.",
            "Ajustes recentes de conteúdo e posicionamento de funcionalidades principais.",
        ],
        "proximos_passos": [
            "Uniformizar copy i18n nas páginas públicas.",
            "Melhorar prova social, métricas e CTA para conversão.",
        ],
        "falta_fazer": [
            "Funil de aquisição com tracking mais profundo e eventos padronizados.",
            "Páginas técnicas/documentação pública por módulo.",
        ],
        "estado_logica": "Boa para fase atual, com evolução focada em conteúdo e internacionalização.",
    },
}


def listar_todo_areas():
    return [{"slug": slug, **dados} for slug, dados in _AREAS_TODO.items()]


def obter_todo_area(slug):
    try:
        return {"slug": slug, **_AREAS_TODO[slug]}
    except KeyError as exc:
        raise Http404("Área TO DO não encontrada.") from exc


def obter_notas_transversais_todo():
    return {
        "selectors_services": (
            "Neste momento estamos a retirar lógica solta para selectors/services em todas as apps. "
            "Há progresso sólido, mas a migração ainda está em curso."
        ),
        "traducao": (
            "Estado atual de tradução: o menu já aparece traduzido em vários contextos, "
            "mas muitos textos internos das páginas e mensagens de backend ainda precisam de cobertura i18n completa."
        ),
    }
