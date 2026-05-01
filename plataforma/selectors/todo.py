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
            "Arquivo técnico de furos terminado já disponível em `Úteis`, com detalhe de snapshot para consulta histórica por superuser.",
            "Dashboard TO DO com visão por app e detalhe de progresso já operacional para superuser.",
            "Revisão global dos templates com cobertura de tradução consolidada em toda a navegação principal.",
            "Nova camada de separação aplicada em `plataforma/views/empresas.py`: atualização de renovação e alteração de plano agora com processamento centralizado em `services/empresas.py`.",
            "Nova camada de separação aplicada em `plataforma/views/financas.py`: fluxos de checkout e retorno PayPal passaram a orquestração por service, com redução de lógica inline e padronização de mensagens por nível.",
            "Nova camada adicional em `plataforma/views/financas.py`: fluxos GET/POST de saída financeira e configuração PayPal unificados em builders (`processar_fluxo_saida_financeira` e `processar_fluxo_configuracao_paypal`) em `services/financas.py`.",
            "Nova camada de separação aplicada em `plataforma/views/planos.py`: create/update de plano unificados num builder (`processar_fluxo_form_plano`) em `services/planos.py`.",
            "Nova camada de separação aplicada em `plataforma/views/subscricoes.py`: construção de contexto da listagem movida para `services/subscricoes.py` (`construir_contexto_subscricao_list`).",
        ],
        "proximos_passos": [
            "Consolidar mais regras em services/selectors para reduzir lógica residual nas views de backoffice.",
            "Fechar ciclo de auditoria de permissões por tipo de conta com cenários automatizados.",
            "Expandir cobertura de internacionalização em mensagens de backend e validações de formulários.",
            "Extrair contextos de detalhe/edição de empresa para services de página e reduzir placeholders de métricas.",
            "Uniformizar ainda mais os fluxos financeiros (entrada/saída/config/paypal) com builders de contexto dedicados por página.",
        ],
        "falta_fazer": [
            "API versionada para operações administrativas críticas.",
            "Testes end-to-end de onboarding/subscrição/pagamento.",
        ],
        "estado_logica": "Boa evolução: separação forte em selectors/services (incluindo empresas e fluxos PayPal em finanças), com pendências pontuais de consolidação.",
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
            "Conector inicial MagCruiser implementado com importação por ficheiro (`CSV/LAS`) e pré-visualização antes de gravar.",
            "Deteção de nome de furo nas medições importadas (ex.: `hole`, `hole_name`, `furo`) com mapeamento automático para furos da empresa.",
            "Modos de aplicação da importação entregues: todas as medições, apenas última por furo, e criação automática de furos em falta.",
            "Relatório de importação já operacional com totais (gravadas/ignoradas/criadas), detalhe por furo e opção de descarregar CSV.",
            "Histórico de importações por empresa guardado em base de dados, visível na página de captura.",
            "Proteção de fallback aplicada na captura para evitar erro 500 quando a tabela de histórico ainda não existe no ambiente.",
            "Nova camada aplicada em `dispositivos/views.py`: fluxo POST da página de captura movido para `services/captura_page.py` (importação e criação de sessão).",
            "Nova camada aplicada: padronização de respostas API com `services/api_flow.py`, reduzindo duplicação em endpoints Bluetooth/USB.",
            "Nova camada aplicada: contextos de dashboard/listagens/detalhes movidos para `services/dashboard_page.py`, com views mais finas.",
            "Nova camada aplicada: captura serial de sessão (`capturar_leitura_serial_view`) extraída para service dedicado de orquestração.",
            "Nova camada adicional em `dispositivos/views.py`: respostas HTTP de endpoints API Bluetooth/USB padronizadas via helper único (`construir_http_response_operacao_api`) no `services/api_flow.py`.",
        ],
        "proximos_passos": [
            "Completar uniformização dos endpoints API restantes para usar o mesmo padrão de resposta/orquestração.",
            "Adicionar validações de consistência para entradas de telemetria em lote.",
            "Adicionar importação dedicada para `XLSX` mantendo o mesmo fluxo (preview -> validação -> gravação).",
            "Melhorar reconciliação automática de nomes de furo com regras de normalização/fuzzy matching configurável por empresa.",
            "Concluir rollout operacional da migração `dispositivos.0006_importacaodispositivohistorico` em todos os ambientes (local e servidor).",
        ],
        "falta_fazer": [
            "API pública para ingestão externa com autenticação forte e versionamento.",
            "Observabilidade detalhada por dispositivo (latência, erro, disponibilidade).",
        ],
        "estado_logica": "Boa evolução e já bastante madura: fluxo MagCruiser funcional, histórico ativo e views principais de Dispositivos mais leves após extração de API flow, contexto de páginas e captura serial; pendências focadas em expansão de formatos e API externa.",
    },
    "projetos": {
        "nome": "Projetos",
        "descricao": "Gestão principal do negócio: projetos, furos, registos, materiais, medições e equipa.",
        "feito": [
            "Fluxos completos para projetos/furos/medições/materiais e operações de campo.",
            "Várias rotas já migradas para services/selectors (empregados, stock, acesso contextual, sugestões).",
            "Suporte a contas individual e empregado com regras específicas de acesso.",
            "Refatorações de UI/UX em páginas de furo 3D e detalhe, incluindo melhorias mobile.",
            "Fluxo de avarias de máquinas com atribuição de responsável, atualização por responsável e notificações por email para envolvidos.",
            "Lista de despesas da empresa evoluída com ações por registo (ver, editar e apagar), incluindo detalhe e confirmação de remoção.",
            "Formulário de despesa atualizado com botão de voltar sem gravar.",
            "Nova camada de separação aplicada em `views/materiais.py`: fluxos de criação/edição e movimentos (levantamento/devolução) consolidados com helpers de orquestração.",
            "Nova camada adicional em `views/materiais.py`: fluxos de entrada/saída de stock e pipeline de formulário create/update passaram a builders em `services/stock.py`, reduzindo repetição na view.",
            "Nova camada adicional em `views/materiais.py`: fluxo GET/POST de levantamento/devolução (initial + bind + submissão) movido para `processar_fluxo_movimento_material_form` em `services/stock.py`.",
            "Nova camada de separação aplicada em `views/despesas.py`: resolução de contexto (admin/individual) e submissão de formulários centralizadas.",
            "Nova camada adicional em `views/despesas.py`: update e delete administrativo agora também orquestrados por service (`processar_submissao_form_despesa_update` e `processar_acao_apagar_despesa`).",
            "Nova camada adicional em `views/despesas.py`: fluxos GET/POST de create/update (admin/individual) unificados em builder (`processar_fluxo_form_despesa`) no `services/despesas.py`.",
            "Nova camada de separação aplicada em `views/registos.py`: submissões de create/update (empregado/admin) e renderização de formulário padronizadas.",
            "Nova camada adicional em `views/registos.py`: fluxos POST/GET de formulário (empregado e admin) extraídos para builders em `services/registos.py`, reduzindo duplicação nas views.",
            "Nova camada de separação aplicada em `views/configuracao_perfuracao.py`: tratamento de `ValidationError` e pipeline create/update (admin/empregado) unificados.",
            "Nova camada adicional em `views/configuracao_perfuracao.py`: fluxos GET/POST de create/update (admin/empregado) movidos para builder em `services/configuracao_perfuracao.py` (`processar_fluxo_form_configuracao_perfuracao`).",
            "Nova camada de separação aplicada em `views/medicoes.py`: render de formulário padronizado e redução de repetição nos fluxos create/update.",
            "Nova camada de separação aplicada em `views/projetos.py`: helpers para `empresa_id`, fluxo de formulário create/update e simplificação de associação de empregado.",
            "Nova camada de separação aplicada em `views/empregados.py`: fluxos de formulário create/update de empregado e adicionar/editar ligação de projeto centralizados em builders de `services/empregados.py`.",
            "Nova camada adicional em `views/empregados.py`: fluxo GET/POST de adição de ficheiro ao empregado centralizado em `processar_fluxo_ficheiro_empregado_admin_form` no service.",
            "Nova camada de separação aplicada em `views/empregado_area.py`: renderização de formulários de edição (individual/empregado) padronizada.",
            "Nova camada adicional em `views/empregado_area.py`: fluxos GET/POST de edição de dados (individual e empregado) extraídos para builders em `services/empregado_area.py`.",
            "Nova camada de separação aplicada em `views/opcoes.py`: resolução de contexto admin e submissão de preferências/definições financeiras centralizadas.",
            "Nova camada adicional em `views/opcoes.py`: fluxos GET/POST de preferências e definições financeiras consolidados em builders no `services/opcoes.py`.",
            "Nova camada de separação aplicada em `views/maquina_avarias.py`: criação de avarias (admin/empregado) unificada com helpers de orquestração.",
            "Nova camada adicional em `views/maquina_avarias.py`: fluxos GET/POST de create/update de avarias migrados para builders em `services/maquina_avarias.py`.",
            "Nova camada de separação aplicada em `views/definicoes.py`: processamento de preferências e ativação de idioma encapsulados em helpers dedicados.",
            "Nova camada adicional em `views/definicoes.py`: fluxo GET/POST do formulário de preferências movido para builder em `services/definicoes.py`.",
            "Nova camada de separação aplicada em `views/maquinas.py`: criação/edição com pipeline de formulário unificado e renderização de formulário padronizada.",
            "Nova camada adicional em `views/maquinas.py`: fluxo create/update delegado para `processar_fluxo_form_maquina` em service, reduzindo duplicação de orquestração HTTP.",
            "Nova camada de separação aplicada em `views/empregado_furo.py`: preparação/renderização de formulário de ligação trabalhador-furo extraídas para helpers reutilizáveis.",
            "Tradução i18n avançada em múltiplos templates operacionais e dashboards.",
            "Revisão final de tradução nos principais templates de detalhe, listagens, exportação e dashboards.",
            "Nova camada de separação em furos concluída: contexto de detalhe, resolução de acesso 3D, fluxos create/list/update, delete e importação 3D externa movidos para services.",
            "Nova camada adicional em `views/furos.py`: orquestração GET/POST de create/update consolidada em builders (`processar_fluxo_form_furo_create`/`processar_fluxo_form_furo_update`) no `services/furo_fluxos.py`.",
            "Lógica pesada do gráfico 3D de furos extraída para service dedicado (`furo_3d_chart`), reduzindo significativamente a complexidade da view.",
            "Uniformização visual em curso: várias páginas críticas já migradas para paleta de botões consistente e menos saturada.",
        ],
        "proximos_passos": [
            "Continuar migração de lógica restante de views para camadas dedicadas, com foco em módulos ainda densos de operação e registos técnicos.",
            "Unificar validações de domínio críticas (ex.: regras de inclinação por tipo de furo).",
            "Reforçar testes de regressão para permissões entre superuser/admin/empregado/individual.",
            "Fechar i18n residual em mensagens transversais e textos técnicos específicos.",
            "Aplicar o mesmo padrão de orquestração por fluxos nas views restantes de operações e registos técnicos.",
            "Concluir varredura visual final para remover estilos legacy com cores vivas remanescentes em templates menos usados.",
        ],
        "falta_fazer": [
            "API versionada para mobile/sensores/drones com contratos estáveis.",
            "Histórico temporal completo de evolução de furo com consultas otimizadas.",
        ],
        "estado_logica": "Boa e em aceleração: além do núcleo de furos, também materiais, despesas (incluindo update/delete), registos, configuração de perfuração, medições, projetos/opções, definições e avarias já receberam nova camada de separação; restam módulos residuais para fechar o ciclo.",
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
            "Nova camada adicional em `geologia/views/logs.py`: fluxos GET/POST de create/update/anexo unificados em builders no `services/logs.py` (`processar_fluxo_*`).",
            "Fluxos de drone (comandos, importação de missão e missão create/update) extraídos para service, reduzindo lógica inline nas views.",
            "Camada Drone S_F também evoluída: criação de comando passou a usar builders/processadores em service (`drone_sf_dashboard`).",
            "APIs bridge do Drone S_F (ingest/comandos/confirmar/log) agora usam resolução comum de autorização em service, removendo repetição nas views.",
            "Ações de missão programada S_F (toggle/executar/remover) extraídas para service, deixando `dashboard.py` mais focado em HTTP/UI.",
            "Nova camada de separação aplicada em `geologia/views/drone.py`: validação de empresa necessária e pipeline de formulário de missão (create/update) consolidados em helpers.",
            "Nova camada de separação aplicada em `geologia/views/dashboard.py`: tratamento de ações POST do detalhe de operação e criação de comando S_F centralizados em helpers.",
            "Nova camada de separação aplicada em `geologia/views/dashboard.py`: fluxos POST do detalhe de operação S_F e criação de comando movidos para `services/drone_sf_page.py`, reduzindo lógica de orquestração na view.",
            "Nova camada aplicada nos endpoints bridge S_F: resolução de contexto (autorização + operação + payload JSON) unificada em helper de service (`resolver_contexto_bridge_sf`), reduzindo duplicação nas APIs de ingest/comandos/confirmação/log.",
            "Nova camada de separação aplicada em `geologia/views/drone.py`: fluxo create/update de missão consolidado em builder `processar_fluxo_form_missao` no service, reduzindo lógica repetida de POST/GET.",
            "Nova camada adicional em `geologia/views/drone.py`: fluxo de importação de missão DJI no hub consolidado em `processar_fluxo_importacao_missao` no service.",
            "Nova camada adicional em `geologia/views/drone.py`: fluxos de atualização do controlo e criação de comando movidos para builders em `services/drone_dashboard.py`.",
            "Nova camada adicional em `geologia/views/dashboard.py`: ações de missão programada S_F (toggle/executar/remover) unificadas em helper único de service (`processar_acao_missao_programada_sf`).",
        ],
        "proximos_passos": [
            "Migrar restantes ações de escrita e importação para services/selectors.",
            "Padronizar validações de missão e trilhas de auditoria operacionais.",
            "Continuar a refatoração dos endpoints bridge para manter padrão único de resposta/orquestração em API.",
        ],
        "falta_fazer": [
            "API de operações em tempo real com autenticação por dispositivo/operador.",
            "Pipeline de dados espaciais para analytics preditivo.",
        ],
        "estado_logica": "Intermédio/boa e a subir: evolução consistente com redução forte de duplicação em logs/drone/dashboard e bridge; pendências agora mais concentradas em fluxos menos centrais e reforço de cobertura de testes.",
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
            "A base já está bem estruturada e houve avanço forte em Projetos (agora também materiais, registos, configuração de perfuração e medições), Furos/Despesas/Avarias e também em Dispositivos (importação MagCruiser com histórico, API flow padronizado e contexto de páginas extraído para services), mas a migração ainda está em curso nas camadas residuais de views/forms/helpers. "
            "No curto prazo, a prioridade operacional em Dispositivos é garantir a migração `0006_importacaodispositivohistorico` aplicada em todos os ambientes para eliminar dependência de fallback."
        ),
        "traducao": (
            "Estado atual de tradução: revisão ampla concluída nos templates visíveis do utilizador, incluindo Projetos, IA, Geologia, Plataforma e Website. "
            "Pontos pendentes concentram-se sobretudo em mensagens de backend/validação e alguns textos técnicos internos, não no menu principal."
        ),
    }
