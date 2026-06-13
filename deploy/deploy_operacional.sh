#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/var/www/sistema_furacao}"
BRANCH="${BRANCH:-main}"
PYTHON_BIN="${PYTHON_BIN:-$APP_DIR/.venv/bin/python}"
PIP_BIN="${PIP_BIN:-$APP_DIR/.venv/bin/pip}"
SERVICE_NAME="${SERVICE_NAME:-sistema_furacao}"
NGINX_SERVICE="${NGINX_SERVICE:-nginx}"
RUN_REPORT_TIMER="${RUN_REPORT_TIMER:-1}"
REPORT_TIMER_NAME="${REPORT_TIMER_NAME:-sf-relatorios-agendados.timer}"
BASE_URL="${BASE_URL:-http://127.0.0.1}"
HEALTHCHECK_PATHS="${HEALTHCHECK_PATHS:-/ /login/ /website/}"
BACKUP_CMD="${BACKUP_CMD:-}"
ROLLBACK_CMD="${ROLLBACK_CMD:-}"
ROLLBACK_ON_ERROR="${ROLLBACK_ON_ERROR:-0}"
DRY_RUN="${DRY_RUN:-1}"

log() {
    printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

run() {
    if [[ "$DRY_RUN" == "1" ]]; then
        printf 'DRY_RUN %q' "$1"
        shift || true
        for arg in "$@"; do
            printf ' %q' "$arg"
        done
        printf '\n'
        return 0
    fi

    "$@"
}

run_shell() {
    if [[ "$DRY_RUN" == "1" ]]; then
        printf 'DRY_RUN %s\n' "$*"
        return 0
    fi

    bash -lc "$*"
}

on_error() {
    local exit_code=$?
    log "Deploy falhou com exit_code=$exit_code"
    if [[ "$ROLLBACK_ON_ERROR" == "1" && -n "$ROLLBACK_CMD" ]]; then
        log "Rollback opcional ativado"
        run_shell "$ROLLBACK_CMD"
    else
        log "Rollback automático não configurado. Define ROLLBACK_ON_ERROR=1 e ROLLBACK_CMD para ativar."
    fi
    exit "$exit_code"
}

trap on_error ERR

log "Deploy operacional Sistema Furação"
log "APP_DIR=$APP_DIR BRANCH=$BRANCH DRY_RUN=$DRY_RUN"

cd "$APP_DIR"

if [[ -n "$BACKUP_CMD" ]]; then
    log "Backup pré-deploy"
    run_shell "$BACKUP_CMD"
else
    log "Backup pré-deploy ignorado: define BACKUP_CMD para ativar."
fi

log "Atualizar código"
run git fetch origin
run git checkout "$BRANCH"
run git pull origin "$BRANCH"

log "Dependências"
run "$PIP_BIN" install -r requirements.txt

log "Validações Django"
run "$PYTHON_BIN" manage.py check
run "$PYTHON_BIN" manage.py check --deploy

log "Base de dados e estáticos"
run "$PYTHON_BIN" manage.py migrate
run "$PYTHON_BIN" manage.py collectstatic --noinput

log "Reiniciar serviços"
run sudo systemctl restart "$SERVICE_NAME"
run sudo systemctl restart "$NGINX_SERVICE"
if [[ "$RUN_REPORT_TIMER" == "1" ]]; then
    run sudo systemctl enable --now "$REPORT_TIMER_NAME"
fi

log "Estado dos serviços"
run sudo systemctl status "$SERVICE_NAME" --no-pager
run sudo systemctl status "$NGINX_SERVICE" --no-pager

log "Healthchecks HTTP"
for path in $HEALTHCHECK_PATHS; do
    url="${BASE_URL%/}${path}"
    run curl -fsSIL "$url"
done

log "Deploy operacional concluído."
