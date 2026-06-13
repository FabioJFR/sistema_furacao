def listar_riscos_deploy():
    return [
        {
            "slug": "website-publico",
            "titulo": "Website público",
            "impacto": "Alto",
            "probabilidade": "Alta",
            "mitigacao": "Validar homepage, planos, registo, feedback, metadata e robots.txt após cada alteração.",
            "dono": "Produto / Frontend / QA",
        },
        {
            "slug": "integracao-apps",
            "titulo": "Integração entre apps",
            "impacto": "Alto",
            "probabilidade": "Alta",
            "mitigacao": "Executar smoke tests ponta a ponta por perfil e por contexto de empresa.",
            "dono": "Backend / QA",
        },
        {
            "slug": "migrations-bd",
            "titulo": "Migrations e estado da base de dados",
            "impacto": "Alto",
            "probabilidade": "Média-alta",
            "mitigacao": "Testar instalação limpa e upgrade sobre base existente antes de deploy.",
            "dono": "Backend / DevOps",
        },
        {
            "slug": "jobs-relatorios",
            "titulo": "Jobs e relatórios agendados",
            "impacto": "Médio-alto",
            "probabilidade": "Média",
            "mitigacao": "Confirmar systemd ativo, execução real do timer, logs e tratamento de falhas.",
            "dono": "DevOps / Backend",
        },
        {
            "slug": "seguranca-uploads",
            "titulo": "Segurança de URL e uploads",
            "impacto": "Alto",
            "probabilidade": "Média",
            "mitigacao": "Validar casos reais de upload e acesso por perfil além dos testes automáticos.",
            "dono": "Backend / QA",
        },
        {
            "slug": "setup-bootstrap",
            "titulo": "Setup local e bootstrap",
            "impacto": "Médio",
            "probabilidade": "Média-alta",
            "mitigacao": "Documentar bootstrap, seeds mínimas e dependências de media e ficheiros locais.",
            "dono": "Backend / DevOps",
        },
        {
            "slug": "fluxos-operacionais",
            "titulo": "Fluxos operacionais densos",
            "impacto": "Médio-alto",
            "probabilidade": "Média",
            "mitigacao": "Rever casos reais de geologia, cartografia, 3D, assiduidade, contratos e compliance.",
            "dono": "Produto / Backend / QA",
        },
    ]


def listar_resumo_riscos_deploy():
    return [
        {
            "titulo": "Mais crítico",
            "descricao": "Website público, integração entre apps e migrations.",
        },
        {
            "titulo": "Mais traiçoeiro",
            "descricao": "Jobs agendados e segurança, porque podem falhar sem ser imediatamente óbvio.",
        },
        {
            "titulo": "Mais estrutural",
            "descricao": "Setup local, porque afeta onboarding, testes e reprodutibilidade.",
        },
    ]


def listar_checklist_pre_deploy():
    return [
        "Confirmar DEBUG=False e SECRET_KEY forte.",
        "Executar check --deploy sem warnings.",
        "Validar migrations em base limpa e em base existente.",
        "Testar homepage, planos, registo público, feedback e robots.txt.",
        "Confirmar configuração do antivírus e políticas de upload.",
        "Executar backup da base de dados e da pasta media.",
    ]


def listar_checklist_pos_deploy():
    return [
        "Confirmar sistema_furacao e nginx ativos via systemctl.",
        "Validar páginas públicas críticas em ambiente real.",
        "Confirmar dashboard principal e fluxos autenticados base.",
        "Verificar execução do timer de relatórios e presença de logs.",
        "Testar um upload real e uma rota protegida por permissões.",
        "Registar qualquer anomalia e respetiva mitigação antes de fechar o deploy.",
    ]


def listar_comandos_deploy_operacional():
    return [
        {
            "titulo": "Simular sem executar",
            "comando": "DRY_RUN=1 bash deploy/deploy_operacional.sh",
            "descricao": "Mostra a sequência completa sem alterar código, base de dados ou serviços.",
        },
        {
            "titulo": "Executar deploy",
            "comando": "DRY_RUN=0 BASE_URL=https://sistemafuracao.pt bash deploy/deploy_operacional.sh",
            "descricao": "Atualiza código, dependências, migrations, static files, serviços e healthchecks.",
        },
        {
            "titulo": "Executar com backup/rollback",
            "comando": "DRY_RUN=0 BACKUP_CMD='pg_dump ...' ROLLBACK_ON_ERROR=1 ROLLBACK_CMD='...' bash deploy/deploy_operacional.sh",
            "descricao": "Permite ligar backup e rollback explícito quando já existe plano validado para a janela de deploy.",
        },
    ]


def listar_comandos_logrotate():
    return [
        {
            "titulo": "Instalar configuração",
            "comando": "sudo cp deploy/logrotate/sistema_furacao /etc/logrotate.d/sistema_furacao",
            "descricao": "Ativa rotação diária dos logs Django e Nginx do Sistema Furação.",
        },
        {
            "titulo": "Validar sintaxe",
            "comando": "sudo logrotate -d /etc/logrotate.d/sistema_furacao",
            "descricao": "Simula a rotação e mostra o que aconteceria sem alterar ficheiros.",
        },
        {
            "titulo": "Forçar rotação controlada",
            "comando": "sudo logrotate -f /etc/logrotate.d/sistema_furacao",
            "descricao": "Executa rotação imediata após validar sintaxe e permissões.",
        },
    ]


def listar_comandos_backup_operacional():
    return [
        {
            "titulo": "Simular backup",
            "comando": "DRY_RUN=1 bash deploy/backup_operacional.sh",
            "descricao": "Mostra criação de pasta, dump PostgreSQL, arquivo media, manifest e limpeza por retenção sem escrever backups.",
        },
        {
            "titulo": "Executar backup",
            "comando": "DRY_RUN=0 BACKUP_DIR=/var/backups/sistema_furacao bash deploy/backup_operacional.sh",
            "descricao": "Cria backup comprimido da base de dados e da pasta media com manifest e checksums.",
        },
        {
            "titulo": "Testar restore",
            "comando": "DRY_RUN=0 RESTORE_TEST_DB=sistema_furacao_restore_test bash deploy/restore_test_operacional.sh",
            "descricao": "Restaura o dump mais recente numa base temporária e valida também o arquivo media.",
        },
        {
            "titulo": "Ativar timers",
            "comando": "sudo cp deploy/systemd/sf-backup-operacional.* deploy/systemd/sf-restore-test-operacional.* /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now sf-backup-operacional.timer sf-restore-test-operacional.timer",
            "descricao": "Agenda backup diário e teste semanal de restore via systemd.",
        },
    ]


def listar_comandos_monitorizacao_operacional():
    return [
        {
            "titulo": "Simular monitorização",
            "comando": "DRY_RUN=1 bash deploy/monitor_disponibilidade.sh",
            "descricao": "Mostra healthchecks HTTP e leitura de 5xx sem enviar alertas.",
        },
        {
            "titulo": "Executar monitor",
            "comando": "DRY_RUN=0 BASE_URL=https://sistemafuracao.pt MAX_5XX_RESPONSES=5 bash deploy/monitor_disponibilidade.sh",
            "descricao": "Valida disponibilidade e dispara alerta se houver indisponibilidade ou 5xx acima do limite.",
        },
        {
            "titulo": "Ativar timer",
            "comando": "sudo cp deploy/systemd/sf-monitor-disponibilidade.* /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now sf-monitor-disponibilidade.timer",
            "descricao": "Agenda execução a cada 5 minutos via systemd.",
        },
    ]


def listar_smoke_test_piloto_mvp():
    return [
        {
            "passo": "Criar projeto",
            "acao": "Entrar como empresa/admin e criar um projeto real com o mínimo de dados.",
            "resultado": "Projeto aparece na lista e fica disponível para furos, máquinas, materiais e registos.",
            "evidencia": "URL/detalhe do projeto ou captura da lista.",
        },
        {
            "passo": "Criar furo",
            "acao": "Criar um furo associado ao projeto usando os defaults do MVP.",
            "resultado": "Furo grava sem exigir campos técnicos completos e mantém configuração técnica editável.",
            "evidencia": "Detalhe do furo com configuração de início visível.",
        },
        {
            "passo": "Criar empregado",
            "acao": "Criar ou aprovar um empregado e confirmar acesso à Minha Área.",
            "resultado": "Empregado vê furos/ações de turno e consegue iniciar registo operacional.",
            "evidencia": "Minha Área do empregado com atalhos de furo, registo, materiais e medições.",
        },
        {
            "passo": "Criar máquina",
            "acao": "Registar uma máquina/sonda operacional e associar depois ao projeto/furo se necessário.",
            "resultado": "Máquina fica ativa, operacional e visível para operação/avarias.",
            "evidencia": "Lista/detalhe de máquinas com estado operacional.",
        },
        {
            "passo": "Lançar registo diário",
            "acao": "Criar um registo diário com projeto, furo, data, metros/observações e, se aplicável, paragem.",
            "resultado": "Registo aparece na área de produção e alimenta dashboard/relatório técnico.",
            "evidencia": "Registo criado e total de registos no dashboard atualizado.",
        },
        {
            "passo": "Validar materiais",
            "acao": "Criar material e testar entrada/levantamento/devolução mínima do fluxo.",
            "resultado": "Material fica rastreável por projeto/furo e quantidade é apresentada corretamente.",
            "evidencia": "Lista de materiais ou movimento de stock criado.",
        },
        {
            "passo": "Registar medição",
            "acao": "Criar uma medição no furo usando a profundidade sugerida e uma observação técnica.",
            "resultado": "Medição guarda snapshot do furo e aparece no histórico/detalhe técnico.",
            "evidencia": "Medição visível no furo ou lista de medições.",
        },
        {
            "passo": "Gerar relatório técnico",
            "acao": "Abrir relatórios do turno/exportação técnica após o registo diário.",
            "resultado": "Admin consegue consultar/exportar dados técnicos sem depender de módulos financeiros.",
            "evidencia": "Página de relatório/exportação técnica carregada sem erro.",
        },
    ]


def listar_tickets_friccoes_piloto_mvp():
    return [
        {
            "fluxo": "Criação",
            "sintoma": "Projeto, furo, empregado ou máquina demora mais de 2 minutos a criar.",
            "ticket": "Reduzir campos obrigatórios, melhorar defaults ou separar campos avançados.",
            "prioridade": "Alta",
            "dono": "Produto / Backend",
        },
        {
            "fluxo": "Turno",
            "sintoma": "Empregado não percebe onde lançar registo, paragem, metros ou observações.",
            "ticket": "Simplificar formulário de registo diário e melhorar orientação contextual do turno.",
            "prioridade": "Alta",
            "dono": "Produto / UX / Backend",
        },
        {
            "fluxo": "Materiais",
            "sintoma": "Material ou movimento de stock não fica claramente associado a projeto/furo.",
            "ticket": "Rever ligação material-projeto-furo e mensagens de confirmação de stock.",
            "prioridade": "Média-alta",
            "dono": "Operação / Backend",
        },
        {
            "fluxo": "Medições",
            "sintoma": "Medição não herda contexto do furo ou não aparece onde o utilizador espera.",
            "ticket": "Rever detalhe do furo, lista de medições e defaults técnicos da medição.",
            "prioridade": "Média-alta",
            "dono": "Produto / Backend",
        },
        {
            "fluxo": "Relatório",
            "sintoma": "Relatório técnico não explica o turno ou exige dados financeiros/comerciais.",
            "ticket": "Separar relatório técnico do modo completo e melhorar campos mínimos do relatório.",
            "prioridade": "Alta",
            "dono": "Produto / Relatórios",
        },
        {
            "fluxo": "Permissões",
            "sintoma": "Admin, empregado ou conta individual vê ações erradas ou fica bloqueado sem motivo claro.",
            "ticket": "Adicionar regressão de permissão por perfil e mensagem de bloqueio mais explícita.",
            "prioridade": "Alta",
            "dono": "Backend / QA",
        },
    ]
