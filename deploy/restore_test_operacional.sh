#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/var/www/sistema_furacao}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sistema_furacao}"
RESTORE_TEST_DB="${RESTORE_TEST_DB:-sistema_furacao_restore_test}"
DROP_RESTORE_DB_AFTER_TEST="${DROP_RESTORE_DB_AFTER_TEST:-1}"
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

shell_quote() {
    printf "%q" "$1"
}

load_env_file() {
    local file="$1"
    local line key value

    [[ -f "$file" ]] || return 0

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"
        [[ "$line" =~ ^[[:space:]]*$ ]] && continue
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ "$line" == export\ * ]] && line="${line#export }"
        [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || continue

        key="${line%%=*}"
        [[ -n "${!key+x}" ]] && continue
        value="${line#*=}"
        value="${value%$'\r'}"
        if [[ "$value" == \"*\" && "$value" == *\" ]]; then
            value="${value:1:${#value}-2}"
        elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
            value="${value:1:${#value}-2}"
        fi
        export "$key=$value"
    done < "$file"
}

if [[ -f "$ENV_FILE" ]]; then
    load_env_file "$ENV_FILE"
fi

DB_USER="${POSTGRES_USER:-${DB_USER:-}}"
DB_PASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}"
DB_HOST="${POSTGRES_HOST:-${DB_HOST:-127.0.0.1}}"
DB_PORT="${POSTGRES_PORT:-${DB_PORT:-5432}}"

if [[ -z "$DB_USER" ]]; then
    log "POSTGRES_USER ou DB_USER não definido."
    exit 2
fi

latest_backup_dir="$(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -n 1 || true)"
if [[ -z "$latest_backup_dir" ]]; then
    log "Nenhum backup encontrado em $BACKUP_DIR."
    exit 3
fi

db_backup="$latest_backup_dir/database.sql.gz"
media_backup="$latest_backup_dir/media.tar.gz"

if [[ ! -f "$db_backup" ]]; then
    log "Backup de base de dados não encontrado: $db_backup"
    exit 4
fi

log "Teste de restore Sistema Furação"
log "BACKUP_DIR=$BACKUP_DIR RESTORE_TEST_DB=$RESTORE_TEST_DB DRY_RUN=$DRY_RUN"

if [[ -n "$DB_PASSWORD" ]]; then
    export PGPASSWORD="$DB_PASSWORD"
fi

db_host_q="$(shell_quote "$DB_HOST")"
db_port_q="$(shell_quote "$DB_PORT")"
db_user_q="$(shell_quote "$DB_USER")"
restore_db_q="$(shell_quote "$RESTORE_TEST_DB")"
db_backup_q="$(shell_quote "$db_backup")"

log "Recriar base temporária de restore"
run_shell "dropdb -h $db_host_q -p $db_port_q -U $db_user_q --if-exists $restore_db_q"
run_shell "createdb -h $db_host_q -p $db_port_q -U $db_user_q $restore_db_q"

log "Restaurar dump mais recente"
run_shell "gzip -dc $db_backup_q | psql -h $db_host_q -p $db_port_q -U $db_user_q $restore_db_q --set ON_ERROR_STOP=on"

log "Validar tabelas restauradas"
run_shell "psql -h $db_host_q -p $db_port_q -U $db_user_q $restore_db_q --tuples-only --command \"select count(*) from information_schema.tables where table_schema='public';\""

if [[ -f "$media_backup" ]]; then
    log "Validar arquivo media"
    run tar -tzf "$media_backup"
else
    log "Arquivo media não encontrado; apenas restore da base de dados foi validado."
fi

if [[ "$DROP_RESTORE_DB_AFTER_TEST" == "1" ]]; then
    log "Remover base temporária de restore"
    run_shell "dropdb -h $db_host_q -p $db_port_q -U $db_user_q --if-exists $restore_db_q"
fi

log "Teste de restore concluído."
