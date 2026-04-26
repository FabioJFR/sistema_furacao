# Deploy Produção (Django + Gunicorn + Nginx)

## 1) Preparar código no servidor

```bash
cd /var/www/sistema_furacao
git fetch origin
git checkout release-v0.9.4
git pull origin release-v0.9.4
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

## 4) Validar segurança e base de dados

```bash
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
```

## 5) Serviços de produção

- Gunicorn systemd: usar modelo em `deploy/systemd/sistema_furacao.service`
- Nginx: usar modelo em `deploy/nginx/sistema_furacao.conf.example`

Recarregar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sistema_furacao
sudo systemctl restart sistema_furacao
sudo systemctl restart nginx
```

## 6) Verificação rápida

```bash
sudo systemctl status sistema_furacao --no-pager
sudo systemctl status nginx --no-pager
curl -I http://127.0.0.1
```

## 7) Backup antes de cada deploy

```bash
pg_dump -h 127.0.0.1 -U <db_user> -d <db_name> > backup_$(date +%F_%H%M).sql
tar -czf media_backup_$(date +%F_%H%M).tar.gz media/
```
