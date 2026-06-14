# Runbook de Disaster Recovery

Objetivo: recuperar o Sistema Furação após perda grave de servidor, base de dados, pasta `media/` ou deploy irrecuperável.

## Objetivos de recuperação

- RTO alvo: 4 horas para serviço mínimo com login, empresas, projetos, furos e registos.
- RPO alvo: 24 horas, assumindo backup diário válido.
- Prioridade de recuperação: base de dados, media, aplicação, Nginx/HTTPS, timers.

## Pré-condições

- Backups em `/var/backups/sistema_furacao` com `database.sql.gz`, `media.tar.gz` e `manifest.txt`.
- Teste semanal de restore ativo por `sf-restore-test-operacional.timer`.
- Acesso ao repositório GitHub e variáveis de ambiente de produção.
- Credenciais PostgreSQL fora do repositório.

## Recuperar servidor novo

```bash
cd /var/www
git clone https://github.com/FabioJFR/sistema_furacao.git
cd sistema_furacao
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env
```

## Restaurar base de dados

Substituir `<backup_dir>` pela pasta do backup escolhido.

```bash
createdb -h 127.0.0.1 -U <db_user> <db_name>
gzip -dc /var/backups/sistema_furacao/<backup_dir>/database.sql.gz | psql -h 127.0.0.1 -U <db_user> <db_name> --set ON_ERROR_STOP=on
```

Depois validar:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate --plan
```

## Restaurar media

```bash
tar -xzf /var/backups/sistema_furacao/<backup_dir>/media.tar.gz -C /var/www/sistema_furacao
sudo chown -R ubuntu:www-data /var/www/sistema_furacao/media
```

## Reinstalar serviços

```bash
sudo cp deploy/systemd/sistema_furacao.service /etc/systemd/system/
sudo cp deploy/systemd/sf-relatorios-agendados.* /etc/systemd/system/
sudo cp deploy/systemd/sf-backup-operacional.* /etc/systemd/system/
sudo cp deploy/systemd/sf-restore-test-operacional.* /etc/systemd/system/
sudo cp deploy/systemd/sf-monitor-disponibilidade.* /etc/systemd/system/
sudo cp deploy/logrotate/sistema_furacao /etc/logrotate.d/sistema_furacao
sudo systemctl daemon-reload
sudo systemctl enable --now sistema_furacao sf-relatorios-agendados.timer sf-backup-operacional.timer sf-restore-test-operacional.timer sf-monitor-disponibilidade.timer
sudo systemctl restart nginx
```

## Validação final

```bash
curl -I https://sistemafuracao.pt
curl -I https://sistemafuracao.pt/login/
DRY_RUN=0 BASE_URL=https://sistemafuracao.pt bash deploy/monitor_disponibilidade.sh
DRY_RUN=0 RESTORE_TEST_DB=sistema_furacao_restore_test bash deploy/restore_test_operacional.sh
```

## Pós-recuperação

- Registar backup usado, hora de início/fim, perda estimada de dados e serviços afetados.
- Confirmar com utilizadores reais se projetos, furos, registos, media e relatórios essenciais estão acessíveis.
- Atualizar este runbook se algum passo falhou, estava incompleto ou demorou mais que o RTO alvo.
