# shellcheck shell=bash
# Common helpers for jfctl: exit codes, logging with redaction, locking,
# safe KEY=VALUE files, confirmation prompts. Sourced by ops/jfctl.

# --- Exit codes (documented in docs/operations/ops-jfctl.md) -----------------
readonly EX_OK=0
readonly EX_ERROR=1        # unexpected failure
readonly EX_USAGE=2        # wrong arguments
readonly EX_PRECHECK=3     # a precondition/preflight check failed, nothing changed
readonly EX_LOCKED=4       # another mutating jfctl command is running
readonly EX_ABORTED=5      # the operator declined a confirmation
readonly EX_VERIFY=6       # post-change verification failed (state described in log)
readonly EX_ROLLEDBACK=7   # change failed and the previous state was restored
readonly EX_NOTINSTALLED=8 # no installation found

# --- Paths (overridable for tests and non-standard layouts) ------------------
JF_ETC=${JFCTL_ETC:-/etc/jf-manager}
JF_OPT=${JFCTL_OPT:-/opt/jf-manager}
JF_LOG_DIR=${JFCTL_LOG_DIR:-/var/log/jf-manager}
JF_LOCK_FILE=${JFCTL_LOCK_FILE:-/run/lock/jfctl.lock}
JF_CONF="$JF_ETC/jfctl.conf"
JF_APP_ENV="$JF_ETC/app.env"
JF_SECRETS_ENV="$JF_ETC/secrets.env"
JF_COMPOSE_ENV="$JF_ETC/compose.env"
JF_TRUSTED_PROXIES="$JF_ETC/trusted-proxies.conf"

JF_ASSUME_YES=${JF_ASSUME_YES:-0}
JF_NONINTERACTIVE=${JF_NONINTERACTIVE:-0}

# Values never written to the log. Filled while loading configuration.
declare -a _JF_REDACT=()

_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

redact() {
    local line=$1 secret
    for secret in "${_JF_REDACT[@]}"; do
        [ ${#secret} -ge 4 ] || continue
        line=${line//"$secret"/***}
    done
    # Generic patterns: URLs with credentials and KEY/PASSWORD/SECRET/TOKEN assignments.
    line=$(printf '%s' "$line" | sed -E \
        -e 's#(://[^:/@ ]+:)[^@ ]+@#\1***@#g' \
        -e 's#((KEY|PASSWORD|PASS|SECRET|TOKEN)[A-Z_]*=)[^ ]+#\1***#g')
    printf '%s' "$line"
}

register_secret() { [ -n "${1:-}" ] && _JF_REDACT+=("$1"); return 0; }

_log_file() {
    [ -n "${JFCTL_NO_LOGFILE:-}" ] && return 0
    if [ -d "$JF_LOG_DIR" ] || mkdir -p "$JF_LOG_DIR" 2>/dev/null; then
        printf '%s %s\n' "$(_ts)" "$(redact "$*")" >>"$JF_LOG_DIR/jfctl.log" 2>/dev/null || true
    fi
}

log()  { _log_file "INFO  $*"; printf '%s\n' "$(redact "$*")"; }
ok()   { _log_file "OK    $*"; printf '  \342\234\223 %s\n' "$(redact "$*")"; }
warn() { _log_file "WARN  $*"; printf '  ! %s\n' "$(redact "$*")" >&2; }
err()  { _log_file "ERROR $*"; printf 'Fehler: %s\n' "$(redact "$*")" >&2; }
step() { _log_file "STEP  $*"; printf '\n==> %s\n' "$(redact "$*")"; }

die() { local code=$1; shift; err "$*"; exit "$code"; }

need_root() {
    [ -n "${JFCTL_ALLOW_NONROOT:-}" ] && return 0
    [ "$(id -u)" -eq 0 ] || die "$EX_PRECHECK" "Dieser Befehl benötigt root-Rechte (sudo jfctl …)."
}

have() { command -v "$1" >/dev/null 2>&1; }

# --- Locking ----------------------------------------------------------------
# One mutating command at a time (install, update, restore, backup, start/stop).
acquire_lock() {
    local what=$1
    mkdir -p "$(dirname "$JF_LOCK_FILE")" 2>/dev/null || true
    exec 9>"$JF_LOCK_FILE" || die "$EX_ERROR" "Sperrdatei $JF_LOCK_FILE nicht beschreibbar."
    if ! flock -n 9; then
        local holder
        holder=$(cat "$JF_LOCK_FILE.owner" 2>/dev/null || echo unbekannt)
        die "$EX_LOCKED" "Ein anderer jfctl-Vorgang läuft bereits ($holder). Bitte warten."
    fi
    printf '%s pid=%s seit %s\n' "$what" "$$" "$(_ts)" >"$JF_LOCK_FILE.owner" 2>/dev/null || true
}

release_lock() { rm -f "$JF_LOCK_FILE.owner" 2>/dev/null || true; flock -u 9 2>/dev/null || true; }

# --- KEY=VALUE files ----------------------------------------------------------
# Files are parsed, never sourced: values may contain shell metacharacters.
# Accepted syntax (shared by systemd EnvironmentFile and Compose env_file):
#   KEY=value          (no spaces, quotes or shell metacharacters)
#   KEY='any value'    (no single quote inside)

_valid_key() { [[ $1 =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; }

# kv_get FILE KEY -> prints value, returns 1 when missing
kv_get() {
    local file=$1 key=$2 line k v
    [ -r "$file" ] || return 1
    while IFS= read -r line || [ -n "$line" ]; do
        [[ $line =~ ^[[:space:]]*(#|$) ]] && continue
        k=${line%%=*}
        [ "$k" = "$key" ] || continue
        v=${line#*=}
        if [[ $v == \'*\' && ${#v} -ge 2 ]]; then v=${v:1:${#v}-2}
        elif [[ $v == \"*\" && ${#v} -ge 2 ]]; then v=${v:1:${#v}-2}
        fi
        printf '%s' "$v"
        return 0
    done <"$file"
    return 1
}

# kv_quote VALUE -> value in the shared syntax
kv_quote() {
    local v=$1
    if [[ $v =~ ^[A-Za-z0-9_@%+=:,./-]*$ ]]; then
        printf '%s' "$v"
    elif [[ $v == *"'"* || $v == *$'\n'* ]]; then
        return 1
    else
        printf "'%s'" "$v"
    fi
}

# kv_set FILE KEY VALUE -> replaces or appends, keeps mode 0600 for new files
kv_set() {
    local file=$1 key=$2 value=$3 quoted tmp
    _valid_key "$key" || die "$EX_USAGE" "Ungültiger Schlüssel: $key"
    quoted=$(kv_quote "$value") || die "$EX_USAGE" "Wert für $key enthält ein Hochkomma oder einen Zeilenumbruch."
    tmp=$(mktemp "$file.XXXXXX")
    if [ -f "$file" ]; then
        chmod --reference="$file" "$tmp" 2>/dev/null || chmod 600 "$tmp"
        awk -v k="$key" -v line="$key=$quoted" '
            BEGIN { done = 0 }
            index($0, k "=") == 1 { if (!done) { print line; done = 1 }; next }
            { print }
            END { if (!done) print line }' "$file" >"$tmp"
    else
        chmod 600 "$tmp"
        printf '%s=%s\n' "$key" "$quoted" >"$tmp"
    fi
    mv -f "$tmp" "$file"
}

kv_unset() {
    local file=$1 key=$2 tmp
    [ -f "$file" ] || return 0
    tmp=$(mktemp "$file.XXXXXX")
    chmod --reference="$file" "$tmp" 2>/dev/null || chmod 600 "$tmp"
    awk -v k="$key" 'index($0, k "=") != 1' "$file" >"$tmp"
    mv -f "$tmp" "$file"
}

# kv_keys FILE -> list of keys
kv_keys() {
    local file=$1 line
    [ -r "$file" ] || return 0
    while IFS= read -r line || [ -n "$line" ]; do
        [[ $line =~ ^[[:space:]]*(#|$) ]] && continue
        _valid_key "${line%%=*}" && printf '%s\n' "${line%%=*}"
    done <"$file"
}

# kv_validate FILE -> fails on lines the shared syntax does not accept
kv_validate() {
    local file=$1 line n=0 k v
    while IFS= read -r line || [ -n "$line" ]; do
        n=$((n + 1))
        [[ $line =~ ^[[:space:]]*(#|$) ]] && continue
        k=${line%%=*}; v=${line#*=}
        if ! _valid_key "$k" || [ "$k" = "$line" ]; then
            err "$file:$n: keine KEY=VALUE-Zeile"; return 1
        fi
        if ! [[ $v =~ ^[A-Za-z0-9_@%+=:,./-]*$ || $v =~ ^\'[^\']*\'$ ]]; then
            err "$file:$n: Wert von $k muss in einfache Hochkommas (ohne Hochkomma im Wert)"; return 1
        fi
    done <"$file"
}

# Loads jfctl.conf into JF_* variables (only known keys).
JF_CONF_KEYS=(JF_MODE JF_VERSION JF_INSTANCE JF_DOMAIN JF_TLS JF_ACME_EMAIL JF_HTTP_BIND
    JF_TRUSTED_PROXY_ADDRS JF_DATA_DIR JF_BACKUP_REPO JF_BACKUP_PASSWORD_FILE
    JF_BACKUP_SCHEDULE JF_BACKUP_KEEP_DAILY JF_BACKUP_KEEP_WEEKLY JF_BACKUP_KEEP_MONTHLY
    JF_TIMEZONE JF_RELEASE_URL JF_BACKEND_IMAGE JF_FRONTEND_IMAGE JF_IMAGE_SOURCE
    JF_POSTGRES_MAJOR JF_VERIFY_ATTESTATION JF_GITHUB_REPO JF_EDGE_SUBNET)

conf_defaults() {
    : "${JF_MODE:=}"
    : "${JF_VERSION:=}"
    : "${JF_INSTANCE:=$(hostname -s 2>/dev/null || echo jf-manager)}"
    : "${JF_DOMAIN:=}"
    : "${JF_TLS:=caddy}"
    : "${JF_ACME_EMAIL:=}"
    : "${JF_HTTP_BIND:=127.0.0.1:8080}"
    : "${JF_TRUSTED_PROXY_ADDRS:=}"
    : "${JF_DATA_DIR:=/var/lib/jf-manager}"
    : "${JF_BACKUP_REPO:=/var/backups/jf-manager/restic}"
    : "${JF_BACKUP_PASSWORD_FILE:=$JF_ETC/backup.pass}"
    : "${JF_BACKUP_SCHEDULE:=*-*-* 02:30:00}"
    : "${JF_BACKUP_KEEP_DAILY:=7}"
    : "${JF_BACKUP_KEEP_WEEKLY:=4}"
    : "${JF_BACKUP_KEEP_MONTHLY:=6}"
    : "${JF_TIMEZONE:=Europe/Berlin}"
    : "${JF_GITHUB_REPO:=Jugendfeuerwehr-Manager/JF-Manager}"
    : "${JF_RELEASE_URL:=https://github.com/$JF_GITHUB_REPO/releases/download}"
    : "${JF_BACKEND_IMAGE:=ghcr.io/jugendfeuerwehr-manager/jf-manager/backend}"
    : "${JF_FRONTEND_IMAGE:=ghcr.io/jugendfeuerwehr-manager/jf-manager/frontend}"
    : "${JF_IMAGE_SOURCE:=registry}"
    : "${JF_POSTGRES_MAJOR:=17}"
    : "${JF_VERIFY_ATTESTATION:=auto}"
    : "${JF_EDGE_SUBNET:=172.30.83.0/24}"
}

conf_load() {
    local key value
    [ -r "$JF_CONF" ] || return 1
    for key in "${JF_CONF_KEYS[@]}"; do
        if value=$(kv_get "$JF_CONF" "$key"); then
            printf -v "$key" '%s' "$value"
        fi
    done
    conf_defaults
    JF_STATE_DIR="$JF_DATA_DIR/state"
    if [ -r "$JF_SECRETS_ENV" ]; then
        register_secret "$(kv_get "$JF_SECRETS_ENV" POSTGRES_PASSWORD || true)"
    fi
    if [ -r "$JF_APP_ENV" ]; then
        local k
        for k in DJANGO_SECRET_KEY FIELD_ENCRYPTION_KEY FIELD_ENCRYPTION_PREVIOUS_KEYS EMAIL_HOST_PASSWORD WEB_PUSH_PRIVATE_KEY; do
            register_secret "$(kv_get "$JF_APP_ENV" "$k" || true)"
        done
    fi
    return 0
}

conf_save() {
    local key
    mkdir -p "$JF_ETC"; chmod 700 "$JF_ETC"
    [ -f "$JF_CONF" ] || { : >"$JF_CONF"; chmod 600 "$JF_CONF"; }
    for key in "${JF_CONF_KEYS[@]}"; do
        kv_set "$JF_CONF" "$key" "${!key:-}"
    done
}

require_installed() {
    conf_load || die "$EX_NOTINSTALLED" "Keine Installation gefunden ($JF_CONF fehlt). Zuerst: jfctl install"
    [ -n "$JF_MODE" ] || die "$EX_NOTINSTALLED" "Betriebsmodus fehlt in $JF_CONF."
}

# --- Secrets ------------------------------------------------------------------
gen_secret() { # length in bytes -> url-safe base64 without padding
    openssl rand -base64 "${1:-32}" | tr -d '\n=' | tr '+/' '-_'
}

gen_fernet_key() { openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n'; }

# --- Prompts -------------------------------------------------------------------
# confirm_phrase "Frage" "erwartete Eingabe" -> 0 only when typed exactly.
confirm_phrase() {
    local question=$1 expected=$2 answer
    if [ "$JF_NONINTERACTIVE" = 1 ] || [ ! -t 0 ]; then
        err "$question – Bestätigung erforderlich, aber kein Terminal. Für Automatisierung: --confirm \"$expected\""
        return 1
    fi
    printf '%s\nZum Bestätigen genau "%s" eingeben: ' "$question" "$expected" >&2
    IFS= read -r answer || return 1
    [ "$answer" = "$expected" ]
}

confirm_yes() {
    local question=$1 answer
    [ "$JF_ASSUME_YES" = 1 ] && return 0
    if [ "$JF_NONINTERACTIVE" = 1 ] || [ ! -t 0 ]; then return 1; fi
    printf '%s [j/N] ' "$question" >&2
    IFS= read -r answer || return 1
    [[ $answer =~ ^[jJyY]$ ]]
}

# ask VAR "Frage" "Vorgabe"
ask() {
    local var=$1 question=$2 default=${3:-} answer
    if [ "$JF_NONINTERACTIVE" = 1 ] || [ ! -t 0 ]; then
        printf -v "$var" '%s' "${!var:-$default}"; return 0
    fi
    printf '%s [%s]: ' "$question" "${!var:-$default}" >&2
    IFS= read -r answer || true
    printf -v "$var" '%s' "${answer:-${!var:-$default}}"
}

# ask_secret VAR "Frage" -> hidden input, empty keeps current value
ask_secret() {
    local var=$1 question=$2 answer
    if [ "$JF_NONINTERACTIVE" = 1 ] || [ ! -t 0 ]; then return 0; fi
    printf '%s (Eingabe verdeckt, leer = generieren/behalten): ' "$question" >&2
    IFS= read -rs answer || true
    printf '\n' >&2
    [ -n "$answer" ] && printf -v "$var" '%s' "$answer"
    return 0
}

# --- State ---------------------------------------------------------------------
state_dir() { mkdir -p "$JF_STATE_DIR"; chmod 750 "$JF_STATE_DIR"; printf '%s' "$JF_STATE_DIR"; }

state_write_json() { # name json
    local dir tmp
    dir=$(state_dir); tmp=$(mktemp "$dir/.$1.XXXXXX")
    printf '%s\n' "$2" >"$tmp"; chmod 644 "$tmp"; mv -f "$tmp" "$dir/$1"
}

# Read-only copy for the web application (OPS-03.4); never contains secrets.
public_write_json() { # name json
    local dir="$JF_DATA_DIR/ops-public" tmp
    mkdir -p "$dir"; chmod 755 "$dir"
    tmp=$(mktemp "$dir/.$1.XXXXXX")
    printf '%s\n' "$2" >"$tmp"; chmod 644 "$tmp"; mv -f "$tmp" "$dir/$1"
}

json_str() { # escape for JSON string content
    local s=$1
    s=${s//\\/\\\\}; s=${s//\"/\\\"}; s=${s//$'\n'/\\n}; s=${s//$'\t'/\\t}
    printf '"%s"' "$s"
}

# version_cmp A B -> prints -1, 0 or 1 (semantic versions, optional "v" prefix)
version_cmp() {
    local a=${1#v} b=${2#v}
    if [ "$a" = "$b" ]; then echo 0; return; fi
    if [ "$(printf '%s\n%s\n' "$a" "$b" | sort -V | head -1)" = "$a" ]; then echo -1; else echo 1; fi
}

valid_version() { [[ ${1#v} =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; }

free_bytes() { df -PB1 "$1" 2>/dev/null | awk 'NR==2 {print $4}'; }

human_bytes() { numfmt --to=iec --suffix=B "${1:-0}" 2>/dev/null || printf '%s B' "$1"; }
