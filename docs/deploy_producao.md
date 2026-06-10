# Deploy Produção (Django + Gunicorn + Nginx)

## 1) Preparar código no servidor

```bash
cd /var/www/sistema_furacao
git fetch origin
git checkout release-v0.9.7
git pull origin release-v0.9.7
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
