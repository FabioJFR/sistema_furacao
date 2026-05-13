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
