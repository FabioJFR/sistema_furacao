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
