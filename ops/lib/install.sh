# shellcheck shell=bash
# jfctl install: collects every answer first, runs all preflight checks,
# shows a summary and only then changes the system. Steps are recorded in
# /etc/jf-manager/install.state so an interrupted run resumes where it stopped.

INSTALL_STEPS=(packages config release runtime database migrate start backup-repo timers admin first-backup verify)

# Keys an answer file may contain (besides the jfctl.conf keys).
INSTALL_EXTRA_KEYS=(JF_ACTION JF_IMPORT_DIR JF_ADMIN_USER JF_ADMIN_EMAIL JF_ADMIN_PASSWORD JF_BACKUP_PASSWORD
    JF_RESTORE_SNAPSHOT JF_RELEASE_DIR EMAIL_HOST EMAIL_PORT EMAIL_HOST_USER EMAIL_HOST_PASSWORD
    EMAIL_USE_TLS EMAIL_USE_SSL DEFAULT_FROM_EMAIL)

_install_state() { printf '%s' "$JF_ETC/install.state"; }
_step_done() { [ "$(kv_get "$(_install_state)" "STEP_${1//-/_}" 2>/dev/null)" = "done" ]; }
_step_mark() { kv_set "$(_install_state)" "STEP_${1//-/_}" "done"; }

_run_step() { # name function
    if _step_done "$1"; then ok "Schritt $1 bereits erledigt"; return 0; fi
    step "Schritt: $1"
    # Subshell with errexit: a function called in "||"/"if" context would run
    # without set -e and could continue after a failed command.
    local rc=0
    set +e; ( set -e; "$2" ); rc=$?; set -e
    [ "$rc" -eq 0 ] || die "$EX_ERROR" "Schritt $1 fehlgeschlagen (Code $rc). Nach Behebung erneut: jfctl install (setzt hier fort)."
    _step_mark "$1"
}

# Answer files may hold secrets: root-owned, not readable by others.
load_answers() {
    local file=$1 key value owner mode
    [ -f "$file" ] || die "$EX_USAGE" "Antwortdatei $file nicht gefunden."
    owner=$(stat -c %u "$file"); mode=$(stat -c %a "$file")
    if [ -z "${JFCTL_ALLOW_NONROOT:-}" ] && [ "$owner" != 0 ]; then die "$EX_PRECHECK" "Antwortdatei muss root gehören."; fi
    [[ $mode =~ ^[0-7]00$ ]] || die "$EX_PRECHECK" "Antwortdatei hat Rechte $mode; erlaubt ist nur Zugriff für den Besitzer (chmod 600)."
    kv_validate "$file" || die "$EX_USAGE" "Antwortdatei fehlerhaft."
    while read -r key; do
        if printf '%s\n' "${JF_CONF_KEYS[@]}" "${INSTALL_EXTRA_KEYS[@]}" | grep -qx "$key"; then
            value=$(kv_get "$file" "$key"); printf -v "$key" '%s' "$value"
            case $key in *PASSWORD*) register_secret "$value" ;; esac
        else
            die "$EX_USAGE" "Unbekannter Schlüssel in der Antwortdatei: $key"
        fi
    done < <(kv_keys "$file")
}

_resolve_latest() {
    curl -fsSL --proto '=https' "https://api.github.com/repos/$JF_GITHUB_REPO/releases/latest" | jq -r '.tag_name // empty' | sed 's/^v//'
}

install_collect() {
    local expert=$1
    : "${JF_ACTION:=install}"
    : "${JF_ADMIN_USER:=admin}"
    : "${JF_ADMIN_EMAIL:=}"
    : "${JF_ADMIN_PASSWORD:=}"
    : "${JF_BACKUP_PASSWORD:=}"
    : "${JF_RESTORE_SNAPSHOT:=latest}"
    : "${JF_RELEASE_DIR:=}"
    : "${JF_IMPORT_DIR:=}"
    conf_defaults

    step "Angaben"
    ask JF_ACTION "Neuinstallation (install), Wiederherstellung aus Sicherung (restore) oder Übernahme eines Exports der Altinstallation (import)" "$JF_ACTION"
    case $JF_ACTION in install|restore|import) ;; *) die "$EX_USAGE" "JF_ACTION muss install, restore oder import sein." ;; esac
    if [ "$JF_ACTION" = import ]; then
        ask JF_IMPORT_DIR "Exportverzeichnis (jfctl migrate legacy-compose)" "$JF_IMPORT_DIR"
        [ -f "$JF_IMPORT_DIR/backup-staging/manifest.json" ] || die "$EX_USAGE" "$JF_IMPORT_DIR ist kein Exportverzeichnis."
    fi
    if [ -z "$JF_MODE" ]; then
        if have docker && docker compose version >/dev/null 2>&1; then JF_MODE=compose; else JF_MODE=native; fi
    fi
    ask JF_MODE "Betriebsmodus: compose (Docker) oder native (Debian 13)" "$JF_MODE"
    case $JF_MODE in compose|native) ;; *) die "$EX_USAGE" "JF_MODE muss compose oder native sein." ;; esac
    ask JF_VERSION "Releaseversion (latest = neueste)" "${JF_VERSION:-latest}"
    if [ "$JF_VERSION" = latest ]; then
        JF_VERSION=$(_resolve_latest) || true
        [ -n "$JF_VERSION" ] || die "$EX_PRECHECK" "Neueste Version nicht ermittelbar; bitte Version angeben."
        log "Neueste Version: $JF_VERSION"
    fi
    JF_VERSION=${JF_VERSION#v}
    valid_version "$JF_VERSION" || die "$EX_USAGE" "Ungültige Version '$JF_VERSION' (erwartet X.Y.Z). Branches werden nicht installiert."
    ask JF_DOMAIN "Domain der Anwendung (z. B. jf.example.org)" "$JF_DOMAIN"
    ask JF_TIMEZONE "Zeitzone" "$JF_TIMEZONE"
    ask JF_TLS "HTTPS: caddy (integriert, Zertifikate automatisch) oder proxy (vorhandener Reverse Proxy)" "$JF_TLS"
    if [ "$JF_TLS" = caddy ]; then
        ask JF_ACME_EMAIL "Kontaktadresse für Zertifikate" "${JF_ACME_EMAIL:-$JF_ADMIN_EMAIL}"
    else
        ask JF_HTTP_BIND "Adresse:Port, an der Nginx für den Proxy lauscht" "$JF_HTTP_BIND"
        ask JF_TRUSTED_PROXY_ADDRS "IP-Adresse(n) des Reverse Proxy (Leerzeichen-getrennt)" "$JF_TRUSTED_PROXY_ADDRS"
    fi
    if [ "$expert" = 1 ]; then
        ask JF_INSTANCE "Instanzname (für Bestätigungen)" "$JF_INSTANCE"
        ask JF_DATA_DIR "Datenverzeichnis" "$JF_DATA_DIR"
        ask JF_BACKUP_SCHEDULE "Backup-Zeitplan (systemd OnCalendar)" "$JF_BACKUP_SCHEDULE"
        ask JF_BACKUP_KEEP_DAILY "Aufbewahrung täglich" "$JF_BACKUP_KEEP_DAILY"
        ask JF_BACKUP_KEEP_WEEKLY "Aufbewahrung wöchentlich" "$JF_BACKUP_KEEP_WEEKLY"
        ask JF_BACKUP_KEEP_MONTHLY "Aufbewahrung monatlich" "$JF_BACKUP_KEEP_MONTHLY"
        ask JF_VERIFY_ATTESTATION "Herkunftsnachweis prüfen (auto, required, off)" "$JF_VERIFY_ATTESTATION"
        [ "$JF_MODE" = compose ] && ask JF_EDGE_SUBNET "Docker-Subnetz für Caddy/Nginx" "$JF_EDGE_SUBNET"
    fi
    ask JF_BACKUP_REPO "Backup-Ziel (Restic-Repository: Pfad, sftp:…, s3:…)" "$JF_BACKUP_REPO"
    if [ "$JF_ACTION" = restore ]; then
        ask_secret JF_BACKUP_PASSWORD "Passwort des vorhandenen Backup-Repositorys"
        [ -n "$JF_BACKUP_PASSWORD" ] || die "$EX_USAGE" "Für die Wiederherstellung ist das Backup-Passwort nötig."
        ask JF_RESTORE_SNAPSHOT "Sicherungs-ID (latest = neueste)" "$JF_RESTORE_SNAPSHOT"
    elif [ "$JF_ACTION" = import ]; then
        ask_secret JF_BACKUP_PASSWORD "Backup-Passwort für das neue Repository"
    else
        ask_secret JF_BACKUP_PASSWORD "Backup-Passwort"
        ask JF_ADMIN_USER "Benutzername des ersten Administrators" "$JF_ADMIN_USER"
        ask JF_ADMIN_EMAIL "E-Mail des ersten Administrators" "$JF_ADMIN_EMAIL"
        ask_secret JF_ADMIN_PASSWORD "Administratorpasswort"
    fi
    [ -n "$JF_BACKUP_PASSWORD" ] && register_secret "$JF_BACKUP_PASSWORD"
    [ -n "$JF_ADMIN_PASSWORD" ] && register_secret "$JF_ADMIN_PASSWORD"
    [ -n "${EMAIL_HOST_PASSWORD:-}" ] && register_secret "$EMAIL_HOST_PASSWORD"
    JF_STATE_DIR="$JF_DATA_DIR/state"
    return 0
}

# Listening TCP port? Uses ss when available, otherwise /proc (minimal systems).
_port_in_use() {
    if have ss; then ss -Hltn "sport = :$1" 2>/dev/null | grep -q .; return; fi
    local hex f files=()
    hex=$(printf '%04X' "$1")
    for f in /proc/net/tcp /proc/net/tcp6; do [ -r "$f" ] && files+=("$f"); done
    [ ${#files[@]} -gt 0 ] || return 1
    awk -v p=":$hex" '$4 == "0A" && substr($2, length($2) - 4) == p {found = 1} END {exit !found}' "${files[@]}"
}

install_preflight() {
    local failed=0 free mem port
    step "Vorabprüfung (es wird noch nichts verändert)"
    config_validate || failed=1
    [ -n "$JF_DOMAIN" ] || { err "Domain fehlt"; failed=1; }
    if [ "$JF_ACTION" = install ] && [ -n "$JF_ADMIN_EMAIL" ] && ! [[ $JF_ADMIN_EMAIL =~ ^[^@[:space:]]+@[^@[:space:]]+$ ]]; then
        err "Ungültige Administrator-E-Mail"; failed=1
    fi
    ad_preflight || failed=1
    mkdir -p "$JF_DATA_DIR" 2>/dev/null || true
    free=$(free_bytes "$JF_DATA_DIR")
    if [ -n "$free" ] && [ "$free" -lt $((5 * 1024 * 1024 * 1024)) ]; then
        err "Zu wenig Speicher unter $JF_DATA_DIR: $(human_bytes "$free") frei, mindestens 5 GB nötig"; failed=1
    else ok "Freier Speicher: $(human_bytes "${free:-0}")"; fi
    mem=$(awk '/MemTotal/ {print $2 * 1024}' /proc/meminfo 2>/dev/null || echo 0)
    if [ "$mem" -lt $((1900 * 1024 * 1024)) ]; then err "Mindestens 2 GB RAM nötig (vorhanden $(human_bytes "$mem"))"; failed=1
    else ok "Arbeitsspeicher: $(human_bytes "$mem")"; fi
    if ! _step_done start; then
        local ports=()
        if [ "$JF_TLS" = caddy ]; then ports=(80 443 8080); else ports=("${JF_HTTP_BIND##*:}"); fi
        [ "$JF_MODE" = native ] && ports+=(8000 5432 6379)
        local busy=0
        for port in "${ports[@]}"; do
            if _port_in_use "$port"; then err "Port $port ist belegt"; busy=1; fi
        done
        if [ "$busy" = 0 ]; then ok "Benötigte Ports frei (${ports[*]})"; else failed=1; fi
    fi
    if [ "$JF_TLS" = caddy ] && have getent && ! getent ahosts "$JF_DOMAIN" >/dev/null 2>&1; then
        warn "$JF_DOMAIN löst nicht auf; Zertifikate können erst nach DNS-Eintrag ausgestellt werden"
    fi
    if [ "$JF_ACTION" = install ] && [ -n "$JF_BACKUP_PASSWORD" ] && [ ${#JF_BACKUP_PASSWORD} -lt 12 ]; then
        err "Backup-Passwort zu kurz (mindestens 12 Zeichen)"; failed=1
    fi
    if [ "$JF_ACTION" = install ] && [ -n "$JF_ADMIN_PASSWORD" ] && [ ${#JF_ADMIN_PASSWORD} -lt 12 ]; then
        err "Administratorpasswort zu kurz (mindestens 12 Zeichen)"; failed=1
    fi
    if [ "$JF_ACTION" = restore ]; then
        if have restic; then
            # Password via environment, never as argument.
            if RESTIC_REPOSITORY="$JF_BACKUP_REPO" RESTIC_PASSWORD="$JF_BACKUP_PASSWORD" restic cat config >/dev/null 2>&1; then
                ok "Backup-Repository lesbar, Passwort korrekt"
            else err "Backup-Repository $JF_BACKUP_REPO nicht lesbar oder Passwort falsch"; failed=1; fi
        else
            warn "restic noch nicht installiert – Repository wird vor dem Ersetzen geprüft"
        fi
    fi
    [ "$failed" = 0 ] || return 1
    step "Release $JF_VERSION laden und prüfen"
    INSTALL_RELEASE_DIR=$(release_fetch "$JF_VERSION" "$JF_RELEASE_DIR") || return 1
    ok "Release $JF_VERSION geprüft"
}

install_summary() {
    cat <<EOF

Zusammenfassung
  Aktion:          $JF_ACTION$([ "$JF_ACTION" = restore ] && echo " (Sicherung $JF_RESTORE_SNAPSHOT aus $JF_BACKUP_REPO)")$([ "$JF_ACTION" = import ] && echo " (Export $JF_IMPORT_DIR)")
  Modus:           $JF_MODE
  Version:         $JF_VERSION
  Domain:          $JF_DOMAIN
  HTTPS:           $([ "$JF_TLS" = caddy ] && echo "integriert (Caddy, Kontakt $JF_ACME_EMAIL)" || echo "vorhandener Proxy ($JF_TRUSTED_PROXY_ADDRS → Nginx $JF_HTTP_BIND)")
  Zeitzone:        $JF_TIMEZONE
  Daten:           $JF_DATA_DIR
  Backup:          $JF_BACKUP_REPO, $JF_BACKUP_SCHEDULE, behalten $JF_BACKUP_KEEP_DAILY/$JF_BACKUP_KEEP_WEEKLY/$JF_BACKUP_KEEP_MONTHLY (Tag/Woche/Monat)
  Backup-Passwort: $([ -n "$JF_BACKUP_PASSWORD" ] && echo "angegeben" || echo "wird erzeugt")
$([ "$JF_ACTION" = install ] && echo "  Administrator:   $JF_ADMIN_USER <${JF_ADMIN_EMAIL:-ohne E-Mail}>, Passwort $([ -n "$JF_ADMIN_PASSWORD" ] && echo angegeben || echo 'wird erzeugt')")

EOF
}

# --- steps ----------------------------------------------------------------------
_inst_packages() { ad_install_packages; }

_inst_config() {
    mkdir -p "$JF_ETC"; chmod 700 "$JF_ETC"
    conf_save
    if [ ! -f "$JF_SECRETS_ENV" ]; then
        install -m 600 /dev/null "$JF_SECRETS_ENV"
        kv_set "$JF_SECRETS_ENV" POSTGRES_PASSWORD "$(gen_secret 24)"
    fi
    if [ ! -f "$JF_BACKUP_PASSWORD_FILE" ]; then
        install -m 600 /dev/null "$JF_BACKUP_PASSWORD_FILE"
        if [ -n "$JF_BACKUP_PASSWORD" ]; then printf '%s\n' "$JF_BACKUP_PASSWORD" >"$JF_BACKUP_PASSWORD_FILE"
        else gen_secret 32 >"$JF_BACKUP_PASSWORD_FILE"; echo >>"$JF_BACKUP_PASSWORD_FILE"; fi
    fi
    if [ ! -f "$JF_APP_ENV" ]; then
        install -m 600 /dev/null "$JF_APP_ENV"
        kv_set "$JF_APP_ENV" DJANGO_SECRET_KEY "$(gen_secret 48)"
        kv_set "$JF_APP_ENV" FIELD_ENCRYPTION_KEY "$(gen_fernet_key)"
    fi
    # Values derived from the answers; secrets above stay untouched on resume.
    kv_set "$JF_APP_ENV" DEBUG False
    kv_set "$JF_APP_ENV" ALLOWED_HOSTS "$JF_DOMAIN,localhost,127.0.0.1"
    kv_set "$JF_APP_ENV" CSRF_TRUSTED_ORIGINS "https://$JF_DOMAIN"
    kv_set "$JF_APP_ENV" FRONTEND_URL "https://$JF_DOMAIN"
    kv_set "$JF_APP_ENV" TIME_ZONE "$JF_TIMEZONE"
    kv_set "$JF_APP_ENV" DEFAULT_FROM_EMAIL "${DEFAULT_FROM_EMAIL:-noreply@$JF_DOMAIN}"
    local k
    for k in EMAIL_HOST EMAIL_PORT EMAIL_HOST_USER EMAIL_HOST_PASSWORD EMAIL_USE_TLS EMAIL_USE_SSL; do
        [ -n "${!k:-}" ] && kv_set "$JF_APP_ENV" "$k" "${!k}"
    done
    conf_load
    ok "Konfiguration unter $JF_ETC geschrieben"
}

_inst_release() {
    [ -n "${INSTALL_RELEASE_DIR:-}" ] || INSTALL_RELEASE_DIR=$(release_fetch "$JF_VERSION" "$JF_RELEASE_DIR")
    release_extract "$INSTALL_RELEASE_DIR" "$JF_VERSION"
    switch_current "$JF_VERSION"
    ok "Release $JF_VERSION unter $JF_OPT/current"
}

_inst_runtime() {
    ad_fetch_release "$JF_VERSION" "$JF_OPT/current/release-manifest.json"
    ad_render
    if [ -z "$(kv_get "$JF_APP_ENV" WEB_PUSH_PRIVATE_KEY 2>/dev/null || true)" ]; then
        local keys
        ad_db_start
        keys=$(ad_manage generate_push_keys 2>/dev/null | grep -E '^WEB_PUSH_(PUBLIC|PRIVATE)_KEY=' || true)
        if [ -n "$keys" ]; then
            kv_set "$JF_APP_ENV" WEB_PUSH_PUBLIC_KEY "$(sed -n 's/^WEB_PUSH_PUBLIC_KEY=//p' <<<"$keys")"
            kv_set "$JF_APP_ENV" WEB_PUSH_PRIVATE_KEY "$(sed -n 's/^WEB_PUSH_PRIVATE_KEY=//p' <<<"$keys")"
            kv_set "$JF_APP_ENV" WEB_PUSH_SUBJECT "mailto:${JF_ADMIN_EMAIL:-admin@$JF_DOMAIN}"
            register_secret "$(kv_get "$JF_APP_ENV" WEB_PUSH_PRIVATE_KEY)"
            ok "Web-Push-Schlüssel erzeugt"
        else
            warn "Web-Push-Schlüssel nicht erzeugt (später: jfctl config edit)"
        fi
    fi
}

_inst_database() {
    ad_db_start
    declare -F ad_db_init >/dev/null && ad_db_init
    ok "Datenbank bereit (PostgreSQL $(ad_pg_major))"
}

_inst_migrate() {
    case $JF_ACTION in
        restore) restore_run "$JF_RESTORE_SNAPSHOT" --new-host; return ;;
        import)  restore_run "dir:$JF_IMPORT_DIR" --new-host; return ;;
    esac
    ad_manage migrate --noinput
    ad_manage seed_role_templates || warn "Rollenvorlagen nicht angelegt (später: jfctl maintenance … / Weboberfläche)"
}

_inst_start() {
    ad_start
    ad_health_internal 120 || { err "Backend antwortet nicht"; return 1; }
    ad_health_entry 30 || { err "Nginx antwortet nicht"; return 1; }
    ok "Anwendung läuft"
}

_inst_backup_repo() {
    backup_repo_init
}

_inst_timers() { maintenance_install_timers; }

_inst_admin() {
    [ "$JF_ACTION" != install ] && { ok "Konten stammen aus der Sicherung bzw. dem Export"; return 0; }
    JF_NONINTERACTIVE=1 cmd_admin bootstrap --user "$JF_ADMIN_USER" --email "${JF_ADMIN_EMAIL:-admin@$JF_DOMAIN}"
}

_inst_first_backup() { backup_create manual "Installation"; }

_inst_verify() {
    ad_health_internal 30 && ad_health_entry 10 || return 1
    ad_manage check --deploy --fail-level ERROR >/dev/null || return 1
    ok "Installation geprüft"
}

cmd_install() {
    need_root
    local answers="" expert=0 resume=0
    while [ $# -gt 0 ]; do
        case $1 in
            --answers) answers=$2; shift 2 ;;
            --expert) expert=1; shift ;;
            --mode) JF_MODE=$2; shift 2 ;;
            --version) JF_VERSION=$2; shift 2 ;;
            --release-dir) JF_RELEASE_DIR=$2; shift 2 ;;
            *) die "$EX_USAGE" "Unbekannte Option: $1" ;;
        esac
    done
    acquire_lock install
    if [ -f "$JF_CONF" ]; then
        if [ -f "$(_install_state)" ] && ! _step_done verify; then
            resume=1; conf_load
            log "Unterbrochene Installation gefunden – setze fort."
        else
            die "$EX_PRECHECK" "JF-Manager ist bereits installiert ($JF_CONF). Für Änderungen: jfctl config / update / restore."
        fi
    fi
    if [ -n "$answers" ]; then load_answers "$answers"; JF_NONINTERACTIVE=1; fi
    if [ "$resume" = 1 ]; then
        conf_defaults; JF_ACTION=$(kv_get "$(_install_state)" ACTION || echo install)
        JF_ADMIN_USER=$(kv_get "$(_install_state)" ADMIN_USER || echo admin)
        JF_ADMIN_EMAIL=$(kv_get "$(_install_state)" ADMIN_EMAIL || true)
        JF_RESTORE_SNAPSHOT=$(kv_get "$(_install_state)" RESTORE_SNAPSHOT || echo latest)
        JF_STATE_DIR="$JF_DATA_DIR/state"
        : "${JF_RELEASE_DIR:=$(kv_get "$(_install_state)" RELEASE_DIR || true)}"
        JF_IMPORT_DIR=$(kv_get "$(_install_state)" IMPORT_DIR || true)
    else
        install_collect "$expert"
    fi
    load_adapter
    install_preflight || die "$EX_PRECHECK" "Vorabprüfung fehlgeschlagen – nichts wurde verändert."
    if [ "$resume" = 0 ]; then
        install_summary
        confirm_yes "Mit diesen Angaben installieren?" || die "$EX_ABORTED" "Abgebrochen – nichts wurde verändert."
        mkdir -p "$JF_ETC"; chmod 700 "$JF_ETC"
        install -m 600 /dev/null "$(_install_state)"
        kv_set "$(_install_state)" ACTION "$JF_ACTION"
        kv_set "$(_install_state)" ADMIN_USER "$JF_ADMIN_USER"
        kv_set "$(_install_state)" ADMIN_EMAIL "$JF_ADMIN_EMAIL"
        kv_set "$(_install_state)" RESTORE_SNAPSHOT "$JF_RESTORE_SNAPSHOT"
        kv_set "$(_install_state)" RELEASE_DIR "$JF_RELEASE_DIR"
        kv_set "$(_install_state)" IMPORT_DIR "$JF_IMPORT_DIR"
    fi
    export JF_ADMIN_PASSWORD
    _run_step packages _inst_packages
    _run_step config _inst_config
    _run_step release _inst_release
    _run_step runtime _inst_runtime
    _run_step database _inst_database
    _run_step migrate _inst_migrate
    _run_step start _inst_start
    _run_step backup-repo _inst_backup_repo
    _run_step timers _inst_timers
    _run_step admin _inst_admin
    _run_step first-backup _inst_first_backup
    _run_step verify _inst_verify
    write_ops_status
    cat <<EOF

JF-Manager $JF_VERSION ist eingerichtet: https://$JF_DOMAIN
  - Backup-Passwort jetzt getrennt vom Server aufbewahren: $JF_BACKUP_PASSWORD_FILE
  - Anmeldung als '$JF_ADMIN_USER'; Administratoren richten bei der ersten Anmeldung MFA ein.
  - Fachliche Einrichtung (Organisation, Abteilungen, Rollen, E-Mail) erfolgt in der Weboberfläche.
  - Prüfung jederzeit: jfctl doctor
EOF
}
