# Runbook de Incidente de Produção

Objetivo: reduzir tempo de resposta quando o Sistema Furação fica indisponível, apresenta erros 5xx ou perde funcionalidades críticas de operação no terreno.

## Critérios de severidade

| Severidade | Quando usar | Tempo alvo |
|---|---|---|
| SEV1 | Site indisponível, login bloqueado, perda de dados ou operação de campo parada | primeira resposta em 15 min |
| SEV2 | Funcionalidade crítica degradada, erros 5xx intermitentes ou deploy com regressão | primeira resposta em 30 min |
| SEV3 | Bug com workaround, problema visual ou fluxo secundário afetado | primeira resposta em 1 dia útil |

## RTO/RPO operacionais

- RTO alvo para SEV1: 2 horas até serviço mínimo recuperado.
- RPO alvo para SEV1: 24 horas, alinhado com backup diário.
- RTO alvo para SEV2: 4 horas até mitigação ou rollback.
- RPO alvo para SEV2: sem perda esperada; confirmar base de dados antes de alterar estado.

## Primeiros 10 minutos

1. Confirmar impacto: público, login, dashboard, operação de empresa, empregado ou apenas módulo isolado.
2. Abrir registo de incidente com data/hora, severidade, responsável e hipótese inicial.
3. Parar novas alterações manuais até haver dono técnico do incidente.
4. Consultar estado dos serviços:

```bash
sudo systemctl status sistema_furacao --no-pager
sudo systemctl status nginx --no-pager
sudo journalctl -u sistema_furacao -n 120 --no-pager
sudo tail -n 120 /var/log/nginx/sistema_furacao.error.log
```

## Diagnóstico rápido

```bash
curl -I https://sistemafuracao.pt
curl -I https://sistemafuracao.pt/login/
DRY_RUN=0 BASE_URL=https://sistemafuracao.pt bash deploy/monitor_disponibilidade.sh
python manage.py check --deploy
python manage.py showmigrations --plan | tail -n 30
```

## Mitigação

- Se o erro começou após deploy, usar rollback validado ou voltar ao commit anterior conhecido.
- Se for falha de Nginx/Gunicorn, reiniciar apenas o serviço afetado e confirmar logs.
- Se for falha de base de dados, não executar migrations novas antes de backup e validação.
- Se for problema de upload/media, preservar ficheiros atuais antes de limpar ou mover dados.

## Comunicação

- Atualizar responsável e estado a cada 30 minutos em SEV1.
- Comunicar impacto em linguagem simples: quem está afetado, workaround e próxima atualização.
- Não prometer prazo final sem evidência técnica.

## Fecho do incidente

1. Confirmar healthchecks públicos e fluxo autenticado mínimo.
2. Confirmar logs sem novos erros 5xx críticos.
3. Registar causa raiz provável, mitigação aplicada e ações preventivas.
4. Criar tarefas pequenas para correção definitiva quando a mitigação não for a solução final.
