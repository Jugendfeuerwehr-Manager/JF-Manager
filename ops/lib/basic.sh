# shellcheck shell=bash
# Basic commands: status, doctor, start/stop/restart, logs, config, admin, workers.

cmd_status() {
    require_installed; load_adapter
    local last running
    running=$(ad_running_version)
    printf 'Instanz:     %s\n' "$JF_INSTANCE"
    printf 'Modus:       %s\n' "$JF_MODE"
    printf 'Version:     %s (aktiv: %s)\n' "${JF_VERSION:-?}" "${running:-?}"
    printf 'Adresse:     %s (%s)\n' "${JF_DOMAIN:-–}" "$([ "$JF_TLS" = caddy ] && echo 'integriertes HTTPS' || echo "Reverse Proxy, Nginx an $JF_HTTP_BIND")"
    if last=$(cat "$JF_STATE_DIR/last-backup.json" 2>/dev/null); then
        printf 'Sicherung:   %s %s (%s)\n' "$(jq -r .status <<<"$last")" "$(jq -r .finished <<<"$last")" "$(jq -r '.snapshot // "–"' <<<"$last")"
    else
        printf 'Sicherung:   noch keine\n'
    fi
    if [ -f "$JF_STATE_DIR/update.state" ]; then
        printf 'Update:      %s\n' "$(kv_get "$JF_STATE_DIR/update.state" STAGE || echo '?')"
    fi
    workers_held && printf 'Worker:      ANGEHALTEN (jfctl workers release)\n'
    echo
    ad_status || true
    write_ops_status
}

# Machine-readable summary for monitoring and the read-only web view (OPS-03.4).
write_ops_status() {
    local last='null' held=false
    [ -r "$JF_STATE_DIR/last-backup.json" ] && last=$(cat "$JF_STATE_DIR/last-backup.json")
    workers_held && held=true
    local json
    json="{\"instance\": $(json_str "$JF_INSTANCE"), \"mode\": $(json_str "$JF_MODE"), \"version\": $(json_str "${JF_VERSION:-}"), \"workers_held\": $held, \"last_backup\": $last, \"updated\": $(json_str "$(_ts)")}"
    state_write_json ops-status.json "$json" 2>/dev/null || true
    public_write_json ops-status.json "$json" 2>/dev/null || true
}

cmd_start() {
    need_root; require_installed; load_adapter; acquire_lock start
    [ -f "$JF_STATE_DIR/update.state" ] && [ "$(kv_get "$JF_STATE_DIR/update.state" STAGE)" != "done" ] &&
        warn "Ein Update ist nicht abgeschlossen ($(kv_get "$JF_STATE_DIR/update.state" STAGE)). Siehe jfctl status."
    step "Starte JF-Manager"
    ad_start
    if ad_health_internal 90 && ad_health_entry 30; then ok "Anwendung erreichbar"; else die "$EX_VERIFY" "Anwendung antwortet nicht (jfctl logs)."; fi
}

cmd_stop() {
    need_root; require_installed; load_adapter; acquire_lock stop
    step "Stoppe JF-Manager"
    ad_stop
    ok "Gestoppt"
}

cmd_restart() { cmd_stop; release_lock; cmd_start; }

cmd_logs() {
    require_installed; load_adapter
    local services=()
    while [ $# -gt 0 ]; do
        case $1 in
            -f|--follow) JF_FOLLOW=1; shift ;;
            -n) JF_LOG_LINES=$2; shift 2 ;;
            jfctl) tail -n "${JF_LOG_LINES:-200}" "$JF_LOG_DIR/jfctl.log"; return ;;
            *) services+=("$1"); shift ;;
        esac
    done
    ad_logs "${services[@]+"${services[@]}"}"
}

cmd_doctor() {
    require_installed; load_adapter
    local problems=0 free key mode v
    _bad() { err "$*"; problems=$((problems + 1)); }

    step "Konfiguration"
    for f in "$JF_CONF" "$JF_APP_ENV" "$JF_SECRETS_ENV"; do
        if [ ! -f "$f" ]; then _bad "$f fehlt"; continue; fi
        mode=$(stat -c %a "$f")
        [ "$mode" = 600 ] && ok "$f (0600)" || _bad "$f hat Rechte $mode, erwartet 0600"
    done
    kv_validate "$JF_APP_ENV" || problems=$((problems + 1))
    for key in DJANGO_SECRET_KEY FIELD_ENCRYPTION_KEY ALLOWED_HOSTS CSRF_TRUSTED_ORIGINS FRONTEND_URL; do
        v=$(kv_get "$JF_APP_ENV" "$key" || true)
        if [ -z "$v" ] || [[ $v == CHANGE_ME* ]]; then _bad "$key fehlt in app.env"; else ok "$key gesetzt"; fi
    done
    [ -f "$JF_BACKUP_PASSWORD_FILE" ] && ok "Backup-Passwortdatei vorhanden" || _bad "Backup-Passwortdatei $JF_BACKUP_PASSWORD_FILE fehlt"

    step "Plattform"
    ad_preflight || problems=$((problems + 1))
    free=$(free_bytes "$JF_DATA_DIR")
    if [ -n "$free" ] && [ "$free" -lt $((2 * 1024 * 1024 * 1024)) ]; then
        _bad "Wenig freier Speicher unter $JF_DATA_DIR: $(human_bytes "$free")"
    else ok "Freier Speicher $(human_bytes "${free:-0}")"; fi

    step "Dienste"
    if ad_health_internal 3; then ok "Backend antwortet"; else _bad "Backend antwortet nicht"; fi
    if ad_health_entry 3; then ok "Nginx antwortet"; else _bad "Nginx antwortet nicht"; fi
    if workers_held; then warn "Worker angehalten (nach Restore)"; elif ad_worker_running; then ok "Worker laufen"; else _bad "Worker laufen nicht"; fi

    step "Anwendung"
    if ad_manage check --deploy --fail-level ERROR >/dev/null 2>&1; then ok "manage.py check --deploy"; else _bad "manage.py check --deploy meldet Fehler"; fi
    if ad_manage migrate --check >/dev/null 2>&1; then ok "Keine offenen Migrationen"; else _bad "Offene oder fehlerhafte Migrationen"; fi

    step "Sicherung und Wartung"
    if [ -r "$JF_STATE_DIR/last-backup.json" ]; then
        local status finished age
        status=$(jq -r .status "$JF_STATE_DIR/last-backup.json"); finished=$(jq -r .finished "$JF_STATE_DIR/last-backup.json")
        age=$(( $(date +%s) - $(date -d "$finished" +%s 2>/dev/null || echo 0) ))
        if [ "$status" != ok ]; then _bad "Letzte Sicherung fehlgeschlagen ($finished)"
        elif [ "$age" -gt $((26 * 3600)) ]; then _bad "Letzte erfolgreiche Sicherung älter als 26 h ($finished)"
        else ok "Letzte Sicherung $finished"; fi
    else _bad "Noch keine Sicherung"; fi
    if have systemctl && [ -d /run/systemd/system ]; then
        systemctl is-enabled --quiet jf-manager-backup.timer 2>/dev/null && ok "Backup-Timer aktiv" || _bad "Backup-Timer nicht aktiv"
    fi

    echo
    if [ "$problems" -eq 0 ]; then ok "Keine Probleme gefunden"; return 0; fi
    err "$problems Problem(e) gefunden"
    return "$EX_VERIFY"
}

# --- config -------------------------------------------------------------------
JF_CONFIG_EDITABLE=(JF_DOMAIN JF_TLS JF_ACME_EMAIL JF_HTTP_BIND JF_TRUSTED_PROXY_ADDRS
    JF_BACKUP_REPO JF_BACKUP_SCHEDULE JF_BACKUP_KEEP_DAILY JF_BACKUP_KEEP_WEEKLY
    JF_BACKUP_KEEP_MONTHLY JF_TIMEZONE JF_INSTANCE JF_VERIFY_ATTESTATION)

cmd_config() {
    require_installed
    local sub=${1:-show}
    case $sub in
        show)
            local key
            for key in "${JF_CONF_KEYS[@]}"; do printf '%-26s %s\n' "$key" "${!key:-}"; done
            printf '\nAnwendungswerte (%s, ohne Geheimnisse):\n' "$JF_APP_ENV"
            kv_keys "$JF_APP_ENV" | while read -r key; do
                case $key in *KEY*|*PASSWORD*|*SECRET*|*TOKEN*) printf '  %-28s ***\n' "$key" ;;
                    *) printf '  %-28s %s\n' "$key" "$(kv_get "$JF_APP_ENV" "$key")" ;; esac
            done ;;
        set)
            need_root; acquire_lock config
            local key=${2:-} value=${3-}
            [ -n "$key" ] || die "$EX_USAGE" "jfctl config set KEY WERT"
            if printf '%s\n' "${JF_CONFIG_EDITABLE[@]}" | grep -qx "$key"; then
                printf -v "$key" '%s' "$value"
                config_validate || die "$EX_USAGE" "Ungültige Angabe, nichts geändert."
                conf_save
            elif [[ $key =~ ^(EMAIL_|DEFAULT_FROM_EMAIL|ALLOWED_HOSTS|CSRF_TRUSTED_ORIGINS|FRONTEND_URL|WEB_PUSH_|WEBAUTHN_|SECURE_|TRUST_PROXY_SSL_HEADER|AUDIT_|SESSION_|LOG_) ]]; then
                kv_set "$JF_APP_ENV" "$key" "$value"
            else
                die "$EX_USAGE" "$key ist nicht über jfctl änderbar. Schlüssel: jfctl config edit (fachliche Einstellungen: Weboberfläche)."
            fi
            load_adapter; ad_render
            ok "$key gespeichert. Wirksam nach: jfctl restart" ;;
        edit)
            need_root; acquire_lock config
            local tmp; tmp=$(mktemp); cp "$JF_APP_ENV" "$tmp"
            "${EDITOR:-vi}" "$tmp"
            kv_validate "$tmp" || { rm -f "$tmp"; die "$EX_USAGE" "Syntaxfehler, nichts geändert."; }
            install -m 600 "$tmp" "$JF_APP_ENV"; rm -f "$tmp"
            ok "app.env gespeichert. Wirksam nach: jfctl restart" ;;
        *) die "$EX_USAGE" "jfctl config [show | set KEY WERT | edit]" ;;
    esac
}

config_validate() {
    case "$JF_TLS" in caddy|proxy) ;; *) err "JF_TLS muss caddy oder proxy sein"; return 1 ;; esac
    if [ "$JF_TLS" = caddy ]; then
        [[ $JF_DOMAIN =~ ^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+$ ]] ||
            { err "Integriertes HTTPS braucht einen öffentlichen Domainnamen (gefunden: '${JF_DOMAIN}')"; return 1; }
        [[ $JF_ACME_EMAIL =~ ^[^@[:space:]]+@[^@[:space:]]+$ ]] || { err "JF_ACME_EMAIL (Kontakt für Zertifikate) fehlt"; return 1; }
    else
        [[ $JF_HTTP_BIND =~ ^(\[[0-9a-fA-F:]+\]|[0-9.]+):[0-9]{2,5}$ ]] || { err "JF_HTTP_BIND muss ADRESSE:PORT sein"; return 1; }
        [ -n "$JF_TRUSTED_PROXY_ADDRS" ] || { err "JF_TRUSTED_PROXY_ADDRS (Adresse des Reverse Proxy) fehlt"; return 1; }
    fi
    [[ $JF_BACKUP_KEEP_DAILY$JF_BACKUP_KEEP_WEEKLY$JF_BACKUP_KEEP_MONTHLY =~ ^[0-9]+$ ]] || { err "Aufbewahrung muss aus Zahlen bestehen"; return 1; }
    if have systemd-analyze; then
        systemd-analyze calendar "$JF_BACKUP_SCHEDULE" >/dev/null 2>&1 || { err "Ungültiger Zeitplan: $JF_BACKUP_SCHEDULE"; return 1; }
    fi
    return 0
}

# --- admin --------------------------------------------------------------------
# Python snippets read their input from the environment, never from arguments.
_ADMIN_BOOTSTRAP_PY='
import os
from django.contrib.auth import get_user_model
User = get_user_model()
name, email, password = os.environ["JF_ADMIN_USER"], os.environ["JF_ADMIN_EMAIL"], os.environ["JF_ADMIN_PASSWORD"]
if User.objects.filter(is_superuser=True).exists() and os.environ.get("JF_ADMIN_FORCE") != "1":
    print("EXISTS"); raise SystemExit(0)
if User.objects.filter(username=name).exists():
    print("NAME_TAKEN"); raise SystemExit(3)
User.objects.create_superuser(username=name, email=email, password=password)
print("CREATED")
'

_ADMIN_RECOVER_PY='
import os
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from users.models import UserSession
User = get_user_model()
try:
    user = User.objects.get(username=os.environ["JF_ADMIN_USER"])
except User.DoesNotExist:
    print("NOT_FOUND"); raise SystemExit(3)
if os.environ.get("JF_ADMIN_PASSWORD"):
    user.set_password(os.environ["JF_ADMIN_PASSWORD"])
user.is_active = True
user.save()
if os.environ.get("JF_RESET_MFA") == "1":
    # Authenticator app, passkeys and recovery codes (SEC-11.3)
    from users.mfa import reset_mfa
    reset_mfa(user, channel="console")
Session.objects.filter(pk__in=UserSession.objects.filter(user=user).values("session_id")).delete()
print("RECOVERED")
'

cmd_admin() {
    need_root; require_installed; load_adapter
    local sub=${1:-} out
    shift || true
    case $sub in
        bootstrap)
            local user=admin email=${JF_ACME_EMAIL:-} generated=0
            while [ $# -gt 0 ]; do
                case $1 in --user) user=$2; shift 2 ;; --email) email=$2; shift 2 ;; *) die "$EX_USAGE" "Unbekannte Option $1" ;; esac
            done
            ask user "Benutzername des ersten Administrators" "$user"
            ask email "E-Mail-Adresse" "$email"
            JF_ADMIN_PASSWORD=${JF_ADMIN_PASSWORD:-}
            ask_secret JF_ADMIN_PASSWORD "Passwort"
            if [ -z "$JF_ADMIN_PASSWORD" ]; then JF_ADMIN_PASSWORD=$(gen_secret 18); generated=1; fi
            register_secret "$JF_ADMIN_PASSWORD"
            export JF_ADMIN_USER=$user JF_ADMIN_EMAIL=$email JF_ADMIN_PASSWORD
            out=$(admin_python "$_ADMIN_BOOTSTRAP_PY") || die "$EX_ERROR" "Anlegen fehlgeschlagen: $out"
            case $out in
                *CREATED*)
                    ok "Administrator '$user' angelegt."
                    if [ "$generated" = 1 ]; then
                        # Shown once on the terminal, never logged.
                        show_once "  Einmalpasswort: $JF_ADMIN_PASSWORD"
                        printf '  Nach der ersten Anmeldung ändern und MFA einrichten.\n'
                    fi ;;
                *EXISTS*) ok "Es gibt bereits einen Administrator; nichts geändert (Zugang verloren: jfctl admin recover)." ;;
                *NAME_TAKEN*) die "$EX_PRECHECK" "Benutzername '$user' ist vergeben." ;;
            esac ;;
        recover)
            local user="" reset_mfa=0 reset_pw=1
            while [ $# -gt 0 ]; do
                case $1 in
                    --user) user=$2; shift 2 ;;
                    --reset-mfa) reset_mfa=1; shift ;;
                    --keep-password) reset_pw=0; shift ;;
                    *) die "$EX_USAGE" "Unbekannte Option $1" ;;
                esac
            done
            ask user "Benutzername" "$user"
            [ -n "$user" ] || die "$EX_USAGE" "jfctl admin recover --user NAME [--reset-mfa] [--keep-password]"
            JF_ADMIN_PASSWORD=""
            if [ "$reset_pw" = 1 ]; then
                ask_secret JF_ADMIN_PASSWORD "Neues Passwort"
                [ -n "$JF_ADMIN_PASSWORD" ] || JF_ADMIN_PASSWORD=$(gen_secret 18)
                register_secret "$JF_ADMIN_PASSWORD"
            fi
            confirm_yes "Zugang für '$user' wiederherstellen$([ $reset_mfa = 1 ] && echo ', MFA-Gerät und Wiederherstellungscodes löschen')? Alle Sitzungen des Kontos werden beendet." ||
                die "$EX_ABORTED" "Abgebrochen."
            export JF_ADMIN_USER=$user JF_ADMIN_PASSWORD JF_RESET_MFA=$reset_mfa
            out=$(admin_python "$_ADMIN_RECOVER_PY") || die "$EX_ERROR" "Wiederherstellung fehlgeschlagen."
            case $out in
                *RECOVERED*)
                    ok "Zugang für '$user' wiederhergestellt; Sitzungen beendet."
                    if [ "$reset_pw" = 1 ]; then show_once "  Neues Passwort: $JF_ADMIN_PASSWORD"; fi
                    _log_file "AUDIT admin recover user=$user reset_mfa=$reset_mfa reset_password=$reset_pw" ;;
                *NOT_FOUND*) die "$EX_PRECHECK" "Benutzer '$user' nicht gefunden." ;;
            esac ;;
        reset-mfa)
            # Second factor only (authenticator app, passkeys, recovery codes);
            # the only way for superusers, staff and other accounts with
            # mandatory MFA (SEC-11.3).
            local user=""
            while [ $# -gt 0 ]; do
                case $1 in --user) user=$2; shift 2 ;; *) die "$EX_USAGE" "Unbekannte Option $1" ;; esac
            done
            ask user "Benutzername" "$user"
            [ -n "$user" ] || die "$EX_USAGE" "jfctl admin reset-mfa --user NAME"
            confirm_yes "Zwei-Faktor-Anmeldung von '$user' zurücksetzen (Authenticator-App, Passkeys, Wiederherstellungscodes) und alle Sitzungen beenden?" ||
                die "$EX_ABORTED" "Abgebrochen."
            ad_manage reset_mfa --user "$user" || die "$EX_ERROR" "Zurücksetzen fehlgeschlagen (Benutzer vorhanden?)."
            _log_file "AUDIT admin reset-mfa user=$user" ;;
        *) die "$EX_USAGE" "jfctl admin bootstrap [--user NAME --email ADRESSE] | recover --user NAME [--reset-mfa] | reset-mfa --user NAME" ;;
    esac
}

# Prints a secret for the operator only: terminal if available, else stdout.
# Never written to the jfctl log.
show_once() {
    if { : >/dev/tty; } 2>/dev/null; then printf '%s\n' "$1" >/dev/tty; else printf '%s\n' "$1"; fi
}

admin_python() { # code -> runs "manage.py shell" with code on stdin
    if [ "$JF_MODE" = compose ]; then
        dc run --rm --no-deps -T -e DJANGO_COLLECTSTATIC=off \
            -e JF_ADMIN_USER -e JF_ADMIN_EMAIL -e JF_ADMIN_PASSWORD -e JF_ADMIN_FORCE -e JF_RESET_MFA \
            backend python manage.py shell <<<"$1"
    else
        ad_manage shell <<<"$1"
    fi
}

# --- workers ------------------------------------------------------------------
cmd_workers() {
    need_root; require_installed; load_adapter
    case ${1:-status} in
        hold)
            acquire_lock workers; state_dir >/dev/null
            echo "manuell $(_ts)" >"$JF_STATE_DIR/workers-held"; ad_workers_stop; ok "Worker angehalten"; write_ops_status ;;
        release)
            acquire_lock workers
            rm -f "$JF_STATE_DIR/workers-held"; ad_workers_start; ok "Worker freigegeben"; write_ops_status ;;
        status)
            if workers_held; then echo "angehalten: $(cat "$JF_STATE_DIR/workers-held")"
            elif ad_worker_running; then echo "laufen"; else echo "gestoppt"; fi ;;
        *) die "$EX_USAGE" "jfctl workers hold | release | status" ;;
    esac
}
