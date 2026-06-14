# Deploy Produção (Django + Gunicorn + Nginx)

## 1) Preparar código no servidor

```bash
cd /var/www/sistema_furacao
git fetch origin
git checkout main
git pull origin main
```

## 2) Virtualenv e dependências

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Variáveis de ambiente

```bash
cp .env.example .env
nano .env
```

Obrigatório em produção:

- `DJANGO_SECRET_KEY` forte
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=sistemafuracao.pt,www.sistemafuracao.pt,92.5.58.215`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://sistemafuracao.pt,https://www.sistemafuracao.pt`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- `DJANGO_SECURE_SSL_REDIRECT=True`
- `DJANGO_SESSION_COOKIE_SECURE=True`
- `DJANGO_CSRF_COOKIE_SECURE=True`
- `DJANGO_SECURE_HSTS_SECONDS=31536000`
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True`
- `DJANGO_SECURE_HSTS_PRELOAD=True`
- `RATE_LIMIT_TRUST_X_FORWARDED_FOR=True` apenas quando o reverse proxy controla `X-Forwarded-For`
- `DJANGO_CACHE_BACKEND=django.core.cache.backends.filebased.FileBasedCache`
- `DJANGO_CACHE_LOCATION=/var/cache/sistema_furacao/django` com diretório legível/escrevível pelo serviço
- `UPLOAD_VIRUS_SCAN_ENABLED=True`
- `UPLOAD_VIRUS_SCAN_FAIL_CLOSED=True`

## 4) Validar segurança e base de dados

```bash
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
```

Alternativa assistida pelo repositório:

```bash
DRY_RUN=1 bash deploy/deploy_operacional.sh
DRY_RUN=0 BASE_URL=https://sistemafuracao.pt bash deploy/deploy_operacional.sh
```

Variáveis úteis do script:

- `APP_DIR=/var/www/sistema_furacao`
- `BRANCH=main`
- `BASE_URL=https://sistemafuracao.pt`
- `HEALTHCHECK_PATHS="/ /login/ /website/"`
- `BACKUP_CMD="pg_dump ... && tar -czf media_backup.tar.gz media/"`
- `ROLLBACK_ON_ERROR=1` e `ROLLBACK_CMD="git reset --hard <sha> && python manage.py migrate && sudo systemctl restart sistema_furacao"` apenas quando houver plano de rollback validado
- `DRY_RUN=1` para simular, `DRY_RUN=0` para executar

## 5) Serviços de produção

- Gunicorn systemd: usar modelo em `deploy/systemd/sistema_furacao.service`
- Relatórios executivos agendados: usar `deploy/systemd/sf-relatorios-agendados.service` e `deploy/systemd/sf-relatorios-agendados.timer`
- Nginx: usar modelo em `deploy/nginx/sistema_furacao.conf.example`

Recarregar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sistema_furacao
sudo systemctl restart sistema_furacao
sudo systemctl restart nginx
sudo systemctl enable --now sf-relatorios-agendados.timer
```

## 5.1) Rotação de logs

```bash
sudo cp deploy/logrotate/sistema_furacao /etc/logrotate.d/sistema_furacao
sudo logrotate -d /etc/logrotate.d/sistema_furacao
sudo logrotate -f /etc/logrotate.d/sistema_furacao
```

A configuração roda diariamente:

- `/var/www/sistema_furacao/logs/*.log` com retenção de 14 dias.
- `/var/log/nginx/sistema_furacao*.log` com retenção de 30 dias.

## 5.2) Backups e testes de restore

```bash
DRY_RUN=1 bash deploy/backup_operacional.sh
DRY_RUN=0 BACKUP_DIR=/var/backups/sistema_furacao bash deploy/backup_operacional.sh
DRY_RUN=0 RESTORE_TEST_DB=sistema_furacao_restore_test bash deploy/restore_test_operacional.sh
sudo cp deploy/systemd/sf-backup-operacional.* deploy/systemd/sf-restore-test-operacional.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sf-backup-operacional.timer sf-restore-test-operacional.timer
```

Por defeito, o backup cria uma pasta por execução em `/var/backups/sistema_furacao`, com:

- `database.sql.gz` para a base de dados PostgreSQL.
- `media.tar.gz` para a pasta `media/`.
- `manifest.txt` com metadados e checksums.
- retenção de 14 dias configurável por `RETENTION_DAYS`.

O timer `sf-backup-operacional.timer` corre diariamente às 02:15 e o timer `sf-restore-test-operacional.timer` testa semanalmente o restore numa base temporária `sistema_furacao_restore_test`.

## 5.3) Monitorização de disponibilidade e 5xx

```bash
DRY_RUN=1 bash deploy/monitor_disponibilidade.sh
DRY_RUN=0 BASE_URL=https://sistemafuracao.pt MAX_5XX_RESPONSES=5 bash deploy/monitor_disponibilidade.sh
sudo cp deploy/systemd/sf-monitor-disponibilidade.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sf-monitor-disponibilidade.timer
```

Variáveis úteis:

- `HEALTHCHECK_PATHS="/ /login/ /website/"` define páginas críticas.
- `MAX_5XX_RESPONSES=5` define o limite de respostas 5xx nas últimas linhas do access log.
- `LOG_TAIL_LINES=2000` define a janela de leitura do log Nginx.
- `SLACK_WEBHOOK_URL` envia alerta para Slack quando configurado.
- `ALERT_EMAIL` envia alerta por email se o servidor tiver `mail` configurado.
- `ALERT_COOLDOWN_SECONDS=1800` evita spam de alertas repetidos.

O timer `sf-monitor-disponibilidade.timer` corre a cada 5 minutos.

## 5.4) Runbooks de incidente e disaster recovery

Documentação operacional:

- `docs/runbooks/incidente_producao.md`
- `docs/runbooks/disaster_recovery.md`

Objetivos definidos:

- Incidente SEV1: RTO 2 horas e RPO 24 horas.
- Disaster recovery: RTO 4 horas e RPO 24 horas.

## 5.5) CI/CD e staging

Gate automático no GitHub:

- Workflow: `.github/workflows/ci.yml`.
- Corre em `push`, `pull_request` para `main` e manualmente por `workflow_dispatch`.
- Usa PostgreSQL de CI, instala dependências sem os pacotes macOS `pyobjc-*`, valida scripts shell, executa `check`, `check --deploy`, `migrate`, `makemigrations --check --dry-run`, `test` e `collectstatic`.

Staging espelho recomendado:

- Criar servidor/serviço separado de produção com domínio próprio, por exemplo `staging.sistemafuracao.pt`.
- Usar base de dados, pasta `media/`, secrets, webhooks e timers isolados da produção.
- Aplicar o mesmo `deploy/deploy_operacional.sh`, mas com `BASE_URL` e variáveis de staging.
- Só promover para produção depois do CI verde, deploy em staging e smoke test MVP validado.

## 6) Verificação rápida

```bash
sudo systemctl status sistema_furacao --no-pager
sudo systemctl status nginx --no-pager
curl -I http://127.0.0.1
```

Checklist de segurança antes de abrir ao público:

- confirmar `DEBUG=False`
- confirmar `SECRET_KEY` longa e aleatória
- confirmar HTTPS funcional ponta a ponta
- confirmar `check --deploy` sem warnings
- confirmar que o proxy sobrescreve `X-Forwarded-For` antes de ativar `RATE_LIMIT_TRUST_X_FORWARDED_FOR`
- confirmar que a cache configurada é partilhada pelos workers que aplicam rate limiting
- confirmar antivírus (`clamscan`) instalado e acessível pelo serviço
- confirmar bridge keys de drones apenas por header `X-Bridge-Key`

## 7) Backup antes de cada deploy

```bash
pg_dump -h 127.0.0.1 -U <db_user> -d <db_name> > backup_$(date +%F_%H%M).sql
tar -czf media_backup_$(date +%F_%H%M).tar.gz media/
```

## 8) Riscos e pontos de atenção

| Risco | Impacto | Probabilidade | Mitigação recomendada | Dono sugerido |
|---|---|---:|---|---|
| Website público | Alto | Alta | Validar homepage, planos, registo, feedback, metadata e `robots.txt` após cada alteração | Produto / Frontend / QA |
| Integração entre apps | Alto | Alta | Executar smoke tests ponta a ponta por perfil e por contexto de empresa | Backend / QA |
| Migrations e estado da base de dados | Alto | Média-alta | Testar instalação limpa e upgrade sobre base existente antes de deploy | Backend / DevOps |
| Jobs e relatórios agendados | Médio-alto | Média | Confirmar `systemd` ativo, execução real do timer, logs e tratamento de falhas | DevOps / Backend |
| Segurança de URL e uploads | Alto | Média | Validar casos reais de upload e acesso por perfil além dos testes automáticos | Backend / QA |
| Setup local e bootstrap | Médio | Média-alta | Documentar bootstrap, seeds mínimas e dependências de `media/` e ficheiros locais | Backend / DevOps |
| Fluxos operacionais densos | Médio-alto | Média | Rever casos reais de geologia, cartografia, 3D, assiduidade, contratos e compliance | Produto / Backend / QA |

Leitura rápida:

- Mais crítico: `website público`, `integração entre apps`, `migrations`
- Mais traiçoeiro: `jobs agendados` e `segurança`, porque podem falhar sem ser imediatamente óbvio
- Mais estrutural: `setup local`, porque afeta onboarding, testes e reprodutibilidade
