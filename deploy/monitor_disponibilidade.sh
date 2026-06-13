#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/var/www/sistema_furacao}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"

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

json_escape() {
    sed 's/\\/\\\\/g; s/"/\\"/g' <<< "$1" | tr '\n' ' '
}

send_alert() {
    local message="$1"
    local escaped
    escaped="$(json_escape "$message")"

    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        log "Enviar alerta Slack"
        run curl -fsS -X POST -H "Content-Type: application/json" --data "{\"text\":\"$escaped\"}" "$SLACK_WEBHOOK_URL"
    else
        log "Slack webhook não configurado; alerta Slack ignorado."
    fi

    if [[ -n "$ALERT_EMAIL" ]]; then
        log "Enviar alerta email"
        if command -v mail >/dev/null 2>&1; then
            if [[ "$DRY_RUN" == "1" ]]; then
                printf 'DRY_RUN printf %%s %q | mail -s %q %q\n' "$message" "Sistema Furação - alerta disponibilidade" "$ALERT_EMAIL"
            else
                printf '%s\n' "$message" | mail -s "Sistema Furação - alerta disponibilidade" "$ALERT_EMAIL"
            fi
        else
            log "Comando mail não encontrado; configurar mailutils/postfix ou usar SLACK_WEBHOOK_URL."
        fi
    else
        log "ALERT_EMAIL não configurado; alerta email ignorado."
    fi
}

if [[ -f "$ENV_FILE" ]]; then
    load_env_file "$ENV_FILE"
fi

BASE_URL="${BASE_URL:-https://sistemafuracao.pt}"
HEALTHCHECK_PATHS="${HEALTHCHECK_PATHS:-/ /login/ /website/}"
NGINX_ACCESS_LOG="${NGINX_ACCESS_LOG:-/var/log/nginx/sistema_furacao.access.log}"
LOG_TAIL_LINES="${LOG_TAIL_LINES:-2000}"
MAX_5XX_RESPONSES="${MAX_5XX_RESPONSES:-5}"
ALERT_COOLDOWN_SECONDS="${ALERT_COOLDOWN_SECONDS:-1800}"
STATE_DIR="${STATE_DIR:-/var/tmp/sistema_furacao_monitor}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
DRY_RUN="${DRY_RUN:-1}"

log "Monitor de disponibilidade Sistema Furação"
log "BASE_URL=$BASE_URL HEALTHCHECK_PATHS=$HEALTHCHECK_PATHS MAX_5XX_RESPONSES=$MAX_5XX_RESPONSES DRY_RUN=$DRY_RUN"

issues=()

for path in $HEALTHCHECK_PATHS; do
    url="${BASE_URL%/}${path}"
    if [[ "$DRY_RUN" == "1" ]]; then
        printf 'DRY_RUN curl -fsS -o /dev/null -w %%{http_code} --max-time 15 %q\n' "$url"
        continue
    fi

    http_code="$(curl -fsS -o /dev/null -w '%{http_code}' --max-time 15 "$url" || true)"
    if [[ -z "$http_code" || "$http_code" == "000" ]]; then
        issues+=("Indisponibilidade: $url sem resposta HTTP.")
    elif [[ "$http_code" =~ ^5 ]]; then
        issues+=("Erro 5xx no healthcheck: $url devolveu HTTP $http_code.")
    elif [[ ! "$http_code" =~ ^[23] ]]; then
        issues+=("Resposta inesperada no healthcheck: $url devolveu HTTP $http_code.")
    fi
done

recent_5xx=0
if [[ -f "$NGINX_ACCESS_LOG" ]]; then
    recent_5xx="$(tail -n "$LOG_TAIL_LINES" "$NGINX_ACCESS_LOG" | awk '($9 ~ /^5/) {count++} END {print count+0}')"
else
    log "Log Nginx não encontrado: $NGINX_ACCESS_LOG"
fi

if (( recent_5xx >= MAX_5XX_RESPONSES )); then
    issues+=("Threshold 5xx excedido: $recent_5xx respostas 5xx nas últimas $LOG_TAIL_LINES linhas de $NGINX_ACCESS_LOG.")
fi

if (( ${#issues[@]} == 0 )); then
    log "Monitor concluído sem alertas."
    exit 0
fi

run mkdir -p "$STATE_DIR"
state_file="$STATE_DIR/last_alert_at"
now="$(date +%s)"
last_alert_at=0
if [[ -f "$state_file" ]]; then
    last_alert_at="$(cat "$state_file" 2>/dev/null || printf '0')"
fi

if (( now - last_alert_at < ALERT_COOLDOWN_SECONDS )); then
    log "Alerta suprimido por cooldown ($ALERT_COOLDOWN_SECONDS segundos)."
    printf '%s\n' "${issues[@]}"
    exit 1
fi

alert_message="Sistema Furação - alerta de disponibilidade em $(date '+%Y-%m-%d %H:%M:%S')"
for issue in "${issues[@]}"; do
    alert_message+=$'\n'"- $issue"
done

send_alert "$alert_message"

if [[ "$DRY_RUN" != "1" ]]; then
    printf '%s\n' "$now" > "$state_file"
fi

printf '%s\n' "$alert_message"
exit 1
