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
            "Dashboard TO DO com visão por app e detalhe de progresso já operacional para superuser.",
            "Revisão global dos templates com cobertura de tradução consolidada em toda a navegação principal.",
        ],
        "proximos_passos": [
            "Consolidar mais regras em services/selectors para reduzir lógica residual nas views.",
            "Fechar ciclo de auditoria de permissões por tipo de conta com cenários automatizados.",
            "Expandir cobertura de internacionalização em mensagens de backend e validações de formulários.",
        ],
        "falta_fazer": [
            "API versionada para operações administrativas críticas.",
            "Testes end-to-end de onboarding/subscrição/pagamento.",
        ],
        "estado_logica": "Boa evolução: separação forte em selectors/services, com pendências pontuais de consolidação.",
    },
    "dispositivos": {
        "nome": "Dispositivos",
        "descricao": "Integração e monitorização de equipamentos e telemetria operacional.",
        "feito": [
            "Dashboard e navegação principal de dispositivos disponível na plataforma.",
            "Estruturas para registo/consulta de leituras e integração operacional já em produção.",
            "Primeira camada de separação aplicada em `dispositivos/views.py`: criação de sessão de captura e registo de dispositivo detectado delegados para services.",
            "Segunda camada aplicada: APIs de escuta e inspeção Bluetooth/USB delegadas para services com validação centralizada.",
            "Terceira camada aplicada: teste de leitura USB (`api_testar_leitura_usb`) movido para service com orquestração de eventos.",
            "Refatoração estrutural concluída: `dispositivos/services/dashboard.py` passou a fachada e a implementação foi dividida em `dashboard_registry`, `dashboard_capture` e `dashboard_discovery`.",
            "Revisão curta final: procura Bluetooth também movida para service e validações duplicadas removidas das views.",
        ],
        "proximos_passos": [
            "Uniformizar todos os fluxos de escrita em services (criação/edição/ações).",
            "Adicionar validações de consistência para entradas de telemetria em lote.",
            "Extrair e consolidar fluxos de teste/leitura e ingestão para reduzir duplicação de mensagens/eventos nas views.",
            "Organizar `dispositivos/services/dashboard.py` em submódulos por responsabilidade para evitar ficheiro monolítico.",
        ],
        "falta_fazer": [
            "API pública para ingestão externa com autenticação forte e versionamento.",
            "Observabilidade detalhada por dispositivo (latência, erro, disponibilidade).",
        ],
        "estado_logica": "Intermédio em evolução: principais fluxos operacionais já extraídos para services; próximo passo é refino modular interno dos próprios services.",
    },
    "projetos": {
        "nome": "Projetos",
        "descricao": "Gestão principal do negócio: projetos, furos, registos, materiais, medições e equipa.",
        "feito": [
            "Fluxos completos para projetos/furos/medições/materiais e operações de campo.",
            "Várias rotas já migradas para services/selectors (empregados, stock, acesso contextual, sugestões).",
            "Suporte a contas individual e empregado com regras específicas de acesso.",
            "Refatorações de UI/UX em páginas de furo 3D e detalhe, incluindo melhorias mobile.",
            "Tradução i18n avançada em múltiplos templates operacionais e dashboards.",
            "Revisão final de tradução nos principais templates de detalhe, listagens, exportação e dashboards.",
            "Nova camada de separação em furos concluída: contexto de detalhe, resolução de acesso 3D, fluxos create/list/update, delete e importação 3D externa movidos para services.",
            "Lógica pesada do gráfico 3D de furos extraída para service dedicado (`furo_3d_chart`), reduzindo significativamente a complexidade da view.",
        ],
        "proximos_passos": [
            "Continuar migração de lógica restante de views para camadas dedicadas.",
            "Unificar validações de domínio críticas (ex.: regras de inclinação por tipo de furo).",
            "Reforçar testes de regressão para permissões entre superuser/admin/empregado/individual.",
            "Fechar i18n residual em mensagens transversais e textos técnicos específicos.",
            "Aplicar o mesmo padrão de orquestração por fluxos nas views restantes de operações e registos técnicos.",
        ],
        "falta_fazer": [
            "API versionada para mobile/sensores/drones com contratos estáveis.",
            "Histórico temporal completo de evolução de furo com consultas otimizadas.",
        ],
        "estado_logica": "Boa e em aceleração: núcleo de furos já muito mais limpo, com transição ativa para arquitetura service/selector e pontos residuais mapeados.",
    },
    "ia": {
        "nome": "IA",
        "descricao": "AI Visual, chatbox operacional, memória de trabalho e biblioteca documental.",
        "feito": [
            "Hub IA, chatbox, memória operacional e histórico de análises disponíveis.",
            "Suporte a biblioteca de documentos para contexto operacional da IA.",
            "Exportação/limpeza de datasets IA disponível na área de úteis (superuser).",
            "Melhorias na experiência do chatbox e base para fluxos de respostas guiadas clicáveis.",
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
        "estado_logica": "Intermédio: núcleo funcional em produção, com refatoração contínua para serviços especializados.",
    },
    "geologia": {
        "nome": "Geologia",
        "descricao": "Operação geológica, integração drone e suporte técnico de terreno.",
        "feito": [
            "Hub geologia e interfaces de drone integrados no ecossistema principal.",
            "Refatorações recentes já moveram partes de submissão para services dedicados.",
            "Tradução i18n reforçada em páginas principais de missão/log e dashboard de furo geológico.",
            "Fluxos de logs geológicos (create/update/anexo) agora orquestrados em service dedicado, com views mais leves.",
            "Fluxos de drone (comandos, importação de missão e missão create/update) extraídos para service, reduzindo lógica inline nas views.",
            "Camada Drone S_F também evoluída: criação de comando passou a usar builders/processadores em service (`drone_sf_dashboard`).",
            "APIs bridge do Drone S_F (ingest/comandos/confirmar/log) agora usam resolução comum de autorização em service, removendo repetição nas views.",
            "Ações de missão programada S_F (toggle/executar/remover) extraídas para service, deixando `dashboard.py` mais focado em HTTP/UI.",
        ],
        "proximos_passos": [
            "Migrar restantes ações de escrita e importação para services/selectors.",
            "Padronizar validações de missão e trilhas de auditoria operacionais.",
        ],
        "falta_fazer": [
            "API de operações em tempo real com autenticação por dispositivo/operador.",
            "Pipeline de dados espaciais para analytics preditivo.",
        ],
        "estado_logica": "Intermédio: evolução positiva, ainda com áreas de lógica a consolidar.",
    },
    "website": {
        "nome": "Website",
        "descricao": "Site público, páginas de entrada e jornada comercial/branding.",
        "feito": [
            "Homepage e estrutura pública funcional em produção.",
            "Ajustes recentes de conteúdo e posicionamento de funcionalidades principais.",
            "Páginas públicas principais já com uso consistente de tags de tradução.",
            "Revisão de consistência i18n na jornada pública (home, planos, login e registo).",
        ],
        "proximos_passos": [
            "Refinar copy comercial por idioma (tom e clareza), mantendo consistência com o produto.",
            "Melhorar prova social, métricas e CTA para conversão.",
        ],
        "falta_fazer": [
            "Funil de aquisição com tracking mais profundo e eventos padronizados.",
            "Páginas técnicas/documentação pública por módulo.",
        ],
        "estado_logica": "Boa para a fase atual, com foco em conteúdo, conversão e internacionalização completa.",
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
            "Estamos a retirar lógica solta para selectors/services em todas as apps. "
            "A base já está bem estruturada e houve avanço forte em Projetos/Furos, mas a migração ainda está em curso nas camadas residuais de views/forms/helpers."
        ),
        "traducao": (
            "Estado atual de tradução: revisão ampla concluída nos templates visíveis do utilizador, incluindo Projetos, IA, Geologia, Plataforma e Website. "
            "Pontos pendentes concentram-se sobretudo em mensagens de backend/validação e alguns textos técnicos internos."
        ),
    }
