#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/var/www/sistema_furacao}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sistema_furacao}"
MEDIA_DIR="${MEDIA_DIR:-$APP_DIR/media}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
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

DB_NAME="${POSTGRES_DB:-${DB_NAME:-}}"
DB_USER="${POSTGRES_USER:-${DB_USER:-}}"
DB_PASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}"
DB_HOST="${POSTGRES_HOST:-${DB_HOST:-127.0.0.1}}"
DB_PORT="${POSTGRES_PORT:-${DB_PORT:-5432}}"

if [[ -z "$DB_NAME" || -z "$DB_USER" ]]; then
    log "POSTGRES_DB/POSTGRES_USER ou DB_NAME/DB_USER não definidos."
    exit 2
fi

timestamp="$(date '+%Y%m%d_%H%M%S')"
backup_run_dir="$BACKUP_DIR/$timestamp"
db_backup="$backup_run_dir/database.sql.gz"
media_backup="$backup_run_dir/media.tar.gz"
manifest="$backup_run_dir/manifest.txt"
db_host_q="$(shell_quote "$DB_HOST")"
db_port_q="$(shell_quote "$DB_PORT")"
db_user_q="$(shell_quote "$DB_USER")"
db_name_q="$(shell_quote "$DB_NAME")"
db_backup_q="$(shell_quote "$db_backup")"
media_backup_q="$(shell_quote "$media_backup")"
manifest_q="$(shell_quote "$manifest")"

log "Backup operacional Sistema Furação"
log "APP_DIR=$APP_DIR BACKUP_DIR=$BACKUP_DIR MEDIA_DIR=$MEDIA_DIR DRY_RUN=$DRY_RUN RETENTION_DAYS=$RETENTION_DAYS"

run mkdir -p "$backup_run_dir"
run chmod 0750 "$BACKUP_DIR"
run chmod 0750 "$backup_run_dir"

log "Backup da base de dados"
if [[ -n "$DB_PASSWORD" ]]; then
    export PGPASSWORD="$DB_PASSWORD"
fi
run_shell "pg_dump -h $db_host_q -p $db_port_q -U $db_user_q $db_name_q | gzip -9 > $db_backup_q"

log "Backup da pasta media"
if [[ -d "$MEDIA_DIR" ]]; then
    media_parent="$(dirname "$MEDIA_DIR")"
    media_base="$(basename "$MEDIA_DIR")"
    run tar -C "$media_parent" -czf "$media_backup" "$media_base"
else
    log "MEDIA_DIR não existe; a criar arquivo vazio controlado."
    run_shell "tar -czf $media_backup_q --files-from /dev/null"
fi

log "Manifest e checksums"
run_shell "{
    echo 'timestamp=$timestamp'
    echo 'app_dir=$APP_DIR'
    echo 'db_name=$DB_NAME'
    echo 'media_dir=$MEDIA_DIR'
    echo 'database_backup=$db_backup'
    echo 'media_backup=$media_backup'
    sha256sum $db_backup_q $media_backup_q
} > $manifest_q"

log "Limpeza de backups antigos"
run find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime "+$RETENTION_DAYS" -print -exec rm -rf {} +

log "Backup operacional concluído em $backup_run_dir"
