# shellcheck shell=bash
# Restore (OPS-04.2): check everything first, require an explicit
# confirmation, back up the current state, prepare in a temporary database,
# then switch. Sessions are dropped; workers stay held until released.

# app.env keys that describe the target host and are kept on restore. All
# other keys (secret key, encryption keys, e-mail, web push …) come from the backup.
RESTORE_HOST_KEYS=(ALLOWED_HOSTS CSRF_TRUSTED_ORIGINS FRONTEND_URL DEBUG TIME_ZONE)

_restore_merge_env() { # backup-app.env -> new app.env
    local src=$1 tmp key
    tmp=$(mktemp "$JF_APP_ENV.XXXXXX"); chmod 600 "$tmp"
    cp "$src" "$tmp"
    for key in "${RESTORE_HOST_KEYS[@]}"; do
        if kv_get "$JF_APP_ENV" "$key" >/dev/null 2>&1; then kv_set "$tmp" "$key" "$(kv_get "$JF_APP_ENV" "$key")"; fi
    done
    kv_validate "$tmp" || { rm -f "$tmp"; return 1; }
    mv -f "$tmp" "$JF_APP_ENV"
}

restore_preflight() { # id staging-dir -> sets RESTORE_* variables
    local id=$1 staging=$2 bver need free
    step "Vorabprüfung der Sicherung $id (es wird noch nichts ersetzt)"
    if [[ $id != dir:* ]]; then
        restic_env
        have restic || die "$EX_PRECHECK" "restic ist nicht installiert."
        restic cat config >/dev/null 2>&1 ||
            die "$EX_PRECHECK" "Repository $JF_BACKUP_REPO nicht lesbar – Passwort ($JF_BACKUP_PASSWORD_FILE) oder Ziel falsch."
        ok "Repository erreichbar, Passwort korrekt"
    fi
    free=$(free_bytes "$JF_DATA_DIR")
    backup_fetch "$id" "$staging" || die "$EX_PRECHECK" "Sicherung $id nicht verfügbar."
    backup_check_fetched || die "$EX_PRECHECK" "Sicherung $id ist beschädigt – nichts wurde verändert."
    ok "Integrität geprüft (Prüfsumme und Lesbarkeit des Dumps, Schlüssel, Uploads)"
    bver=$(jq -r .app_version "$FETCH_MANIFEST")
    if [ "$(version_cmp "$bver" "${JF_VERSION#v}")" = 1 ]; then
        die "$EX_PRECHECK" "Sicherung stammt von Version $bver, installiert ist ${JF_VERSION}. Zuerst: jfctl update --version $bver"
    fi
    ok "Version kompatibel (Sicherung $bver, Installation ${JF_VERSION#v})"
    # Restored database + current database (kept for rollback) + uploads copy.
    need=$(( $(jq -r .db_dump.bytes "$FETCH_MANIFEST") * 4 + $(jq -r .uploads.bytes "$FETCH_MANIFEST") + 512 * 1024 * 1024 ))
    free=$(free_bytes "$JF_DATA_DIR")
    [ "$free" -ge "$need" ] || die "$EX_PRECHECK" "Zu wenig Speicher: $(human_bytes "$free") frei, $(human_bytes "$need") nötig."
    ok "Speicher ausreichend ($(human_bytes "$free") frei)"
    RESTORE_MANIFEST=$FETCH_MANIFEST RESTORE_STAGING=$FETCH_STAGING RESTORE_UPLOADS=$FETCH_UPLOADS
}

# Database swap with rollback information.
_restore_db_prepare() {
    step "Datenbank vorbereiten (temporäre Datenbank jf_manager_restore)"
    ad_db_start
    ad_db_restore_into jf_manager_restore "$RESTORE_STAGING/db.dump" >/dev/null ||
        { ad_psql 'DROP DATABASE IF EXISTS jf_manager_restore' >/dev/null 2>&1; return 1; }
    local n
    n=$(ad_psql "SELECT count(*) FROM django_migrations" jf_manager_restore 2>/dev/null || echo 0)
    [ "${n:-0}" -gt 0 ] || { err "Vorbereitete Datenbank enthält keine Migrationen"; return 1; }
    ok "Vorbereitete Datenbank gültig ($n Migrationseinträge)"
}

_restore_db_activate() {
    ad_psql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname IN ('jf_manager','jf_manager_restore') AND pid <> pg_backend_pid()" >/dev/null
    ad_psql 'DROP DATABASE IF EXISTS jf_manager_before_restore' >/dev/null
    if [ "$(ad_psql "SELECT 1 FROM pg_database WHERE datname='jf_manager'")" = 1 ]; then
        ad_psql 'ALTER DATABASE jf_manager RENAME TO jf_manager_before_restore' >/dev/null
    fi
    ad_psql 'ALTER DATABASE jf_manager_restore RENAME TO jf_manager' >/dev/null
}

_restore_db_rollback() {
    ad_psql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='jf_manager' AND pid <> pg_backend_pid()" >/dev/null 2>&1 || true
    if [ "$(ad_psql "SELECT 1 FROM pg_database WHERE datname='jf_manager_before_restore'" 2>/dev/null)" = 1 ]; then
        ad_psql 'DROP DATABASE IF EXISTS jf_manager' >/dev/null 2>&1 || true
        ad_psql 'ALTER DATABASE jf_manager_before_restore RENAME TO jf_manager' >/dev/null 2>&1 || true
    fi
}

_restore_uploads_activate() {
    local dir prev
    dir=$(ad_uploads_dir); prev="$dir.before-restore"
    rm -rf "$prev"
    [ -d "$dir" ] && mv "$dir" "$prev"
    if [ -n "$RESTORE_UPLOADS" ] && [ -d "$RESTORE_UPLOADS" ]; then
        # Import directories stay intact (copy); restic staging is moved.
        if [ "${FETCH_FROM_DIR:-0}" = 1 ]; then cp -a "$RESTORE_UPLOADS" "$dir"; else mv "$RESTORE_UPLOADS" "$dir"; fi
    else
        mkdir -p "$dir"
    fi
    chown -R "$(ad_uploads_owner)" "$dir" 2>/dev/null || true
    chmod 750 "$dir"
}

_restore_uploads_rollback() {
    local dir; dir=$(ad_uploads_dir)
    [ -d "$dir.before-restore" ] || return 0
    rm -rf "$dir"; mv "$dir.before-restore" "$dir"
}

_DROP_SESSIONS_PY='
from django.contrib.sessions.models import Session
deleted, _ = Session.objects.all().delete()
print(f"SESSIONS_DROPPED {deleted}")
'

# restore_run ID [--new-host] [--confirm NAME]
restore_run() {
    local id=$1; shift
    local new_host=0 confirm="" staging env_backup
    while [ $# -gt 0 ]; do
        case $1 in
            --new-host) new_host=1; shift ;;
            --confirm) confirm=$2; shift 2 ;;
            *) die "$EX_USAGE" "Unbekannte Option: $1" ;;
        esac
    done
    staging="$JF_DATA_DIR/restore-staging"
    restore_preflight "$id" "$staging"

    if [ "$new_host" = 0 ]; then
        cat <<EOF

Wiederherstellung von Sicherung $id
  erstellt:   $(jq -r .created "$RESTORE_MANIFEST") auf $(jq -r .instance "$RESTORE_MANIFEST") ($(jq -r .mode "$RESTORE_MANIFEST"), Version $(jq -r .app_version "$RESTORE_MANIFEST"))
  Ziel:       $JF_INSTANCE ($JF_MODE, Version ${JF_VERSION#v})
  Ersetzt:    Datenbank, Uploads und Anwendungsschlüssel. Alle Sitzungen werden beendet,
              Hintergrundaufträge bleiben bis zur Freigabe angehalten.
  Vorher wird der aktuelle Zustand zusätzlich gesichert.

EOF
        if [ -n "$confirm" ]; then
            [ "$confirm" = "$JF_INSTANCE" ] || die "$EX_ABORTED" "--confirm muss den Instanznamen '$JF_INSTANCE' enthalten."
        else
            confirm_phrase "Alle Daten von '$JF_INSTANCE' werden ersetzt." "$JF_INSTANCE" ||
                { rm -rf "$staging"; die "$EX_ABORTED" "Abgebrochen – nichts wurde verändert."; }
        fi
        step "Aktuellen Zustand sichern"
        ad_entry_stop; ad_workers_stop
        if ! backup_in_window pre-restore "vor Wiederherstellung von $id"; then
            ad_app_start; ad_entry_start; rm -rf "$staging"
            die "$EX_ERROR" "Sicherung des aktuellen Zustands fehlgeschlagen – nichts ersetzt."
        fi
        RESTORE_SAFETY_SNAPSHOT=$BACKUP_LAST_SNAPSHOT
    fi

    if ! _restore_db_prepare; then
        [ "$new_host" = 0 ] && { ad_app_start; ad_entry_start; }
        die "$EX_ERROR" "Vorbereitung fehlgeschlagen – aktueller Zustand unverändert."
    fi

    step "Umschalten"
    ad_app_stop
    env_backup=$(mktemp "$JF_ETC/app.env.before-restore.XXXXXX")
    cp -p "$JF_APP_ENV" "$env_backup"
    if ! { _restore_db_activate && _restore_uploads_activate && _restore_merge_env "$RESTORE_STAGING/config/app.env"; }; then
        err "Umschalten fehlgeschlagen – stelle vorherigen Zustand her"
        _restore_db_rollback; _restore_uploads_rollback; cp -p "$env_backup" "$JF_APP_ENV"
        [ "$new_host" = 0 ] && { ad_render; ad_app_start; ad_entry_start; }
        exit "$EX_ROLLEDBACK"
    fi
    ad_render
    # Hold workers: queued mails/sync/push from the backup are reviewed first.
    state_dir >/dev/null
    echo "restore $id $(_ts)" >"$JF_STATE_DIR/workers-held"
    ad_redis_flush_queues || warn "Redis-Warteschlange nicht geleert"

    step "Schema angleichen und Sitzungen verwerfen"
    if ! ad_manage migrate --noinput >/dev/null || ! ad_manage shell <<<"$_DROP_SESSIONS_PY" >/dev/null; then
        err "Migration nach Wiederherstellung fehlgeschlagen – stelle vorherigen Zustand her"
        _restore_db_rollback; _restore_uploads_rollback; cp -p "$env_backup" "$JF_APP_ENV"
        rm -f "$JF_STATE_DIR/workers-held"
        ad_render; [ "$new_host" = 0 ] && { ad_app_start; ad_entry_start; }
        exit "$EX_ROLLEDBACK"
    fi
    ok "Sitzungen verworfen"

    if [ "$new_host" = 0 ]; then
        ad_app_start
        if ! ad_health_internal 90; then
            die "$EX_VERIFY" "Backend antwortet nach der Wiederherstellung nicht. Vorheriger Stand: Datenbank jf_manager_before_restore, Sicherung ${RESTORE_SAFETY_SNAPSHOT:-–}."
        fi
        ad_entry_start
        ad_health_entry 30 || warn "Nginx antwortet nicht (jfctl logs frontend)"
    fi
    [ "${FETCH_FROM_DIR:-0}" = 1 ] || rm -rf "$staging"
    rm -f "$env_backup"
    _log_file "AUDIT restore snapshot=$id safety=${RESTORE_SAFETY_SNAPSHOT:-none}"
    write_ops_status
    cat <<EOF

Wiederherstellung von $id abgeschlossen.
  - Vorheriger Stand bleibt bis zur nächsten Wiederherstellung als Datenbank
    jf_manager_before_restore und $(ad_uploads_dir).before-restore erhalten$([ -n "${RESTORE_SAFETY_SNAPSHOT:-}" ] && echo ", zusätzlich Sicherung $RESTORE_SAFETY_SNAPSHOT").
  - Hintergrundaufträge (Versand, Synchronisation, Push) sind angehalten. Wartende
    Aufträge in der Weboberfläche prüfen, dann freigeben: jfctl workers release
EOF
}

cmd_restore() {
    need_root; require_installed; load_adapter
    local id=${1:-}
    [ -n "$id" ] && [[ $id != -* ]] || die "$EX_USAGE" "jfctl restore <backup-id> [--confirm INSTANZNAME] (IDs: jfctl backup list)"
    shift
    acquire_lock "restore $id"
    restore_run "$id" "$@"
}
