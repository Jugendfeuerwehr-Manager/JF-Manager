# shellcheck shell=bash
# Backups with Restic (OPS-04.1). One snapshot contains:
#   <data>/backup-staging/db.dump        pg_dump custom format
#   <data>/backup-staging/manifest.json  version, mode, checksums, sizes
#   <data>/backup-staging/config/        app.env (keys!), jfctl.conf, maintenance.conf
#   <data>/uploads/                      private media and attachments
# The logical format is identical for Compose and native installs.

BACKUP_FORMAT=1

_backup_window_end() {
    step "Wartungsfenster beenden"
    ad_app_start >/dev/null 2>&1 || warn "Backend/Worker ließen sich nicht starten (jfctl start)"
    ad_entry_start >/dev/null 2>&1 || warn "Oberfläche ließ sich nicht starten (jfctl start)"
}

restic_env() {
    export RESTIC_REPOSITORY="$JF_BACKUP_REPO"
    export RESTIC_PASSWORD_FILE="$JF_BACKUP_PASSWORD_FILE"
    export RESTIC_CACHE_DIR="${RESTIC_CACHE_DIR:-/var/cache/jf-manager/restic}"
    mkdir -p "$RESTIC_CACHE_DIR" 2>/dev/null || true
    # Optional credentials for remote repositories (s3, sftp …), parsed not sourced.
    if [ -r "$JF_ETC/restic.env" ]; then
        local k
        while read -r k; do export "$k=$(kv_get "$JF_ETC/restic.env" "$k")"; register_secret "${!k}"; done < <(kv_keys "$JF_ETC/restic.env")
    fi
}

backup_repo_init() {
    restic_env
    have restic || die "$EX_PRECHECK" "restic ist nicht installiert."
    [ -s "$JF_BACKUP_PASSWORD_FILE" ] || die "$EX_PRECHECK" "Backup-Passwortdatei $JF_BACKUP_PASSWORD_FILE fehlt oder ist leer."
    if restic cat config >/dev/null 2>&1; then
        ok "Backup-Repository vorhanden ($JF_BACKUP_REPO)"
    else
        case $JF_BACKUP_REPO in /*) mkdir -p "$JF_BACKUP_REPO"; chmod 700 "$JF_BACKUP_REPO" ;; esac
        restic init >/dev/null || die "$EX_ERROR" "Backup-Repository konnte nicht angelegt werden."
        ok "Backup-Repository angelegt ($JF_BACKUP_REPO)"
    fi
}

_backup_status() { # status snapshot message
    local prev_success='null' now
    now=$(_ts)
    if [ -r "$JF_STATE_DIR/last-backup.json" ]; then
        prev_success=$(jq -c '.last_success // null' "$JF_STATE_DIR/last-backup.json" 2>/dev/null || echo null)
    fi
    if [ "$1" = ok ]; then prev_success="{\"finished\": $(json_str "$now"), \"snapshot\": $(json_str "$2")}"; fi
    state_write_json last-backup.json "{\"status\": $(json_str "$1"), \"finished\": $(json_str "$now"), \"snapshot\": $(json_str "$2"), \"message\": $(json_str "$3"), \"last_success\": $prev_success}"
    write_ops_status
}

# backup_create KIND REASON [--in-window]
#   KIND: scheduled | manual | pre-update | pre-restore
#   --in-window: services are already stopped by the caller and stay stopped.
backup_create() {
    local kind=$1 reason=$2 in_window=${3:-} staging dump snap was_running=0 out
    staging="$JF_DATA_DIR/backup-staging"
    restic_env
    have restic || die "$EX_PRECHECK" "restic ist nicht installiert."
    restic cat config >/dev/null 2>&1 || die "$EX_PRECHECK" "Backup-Repository $JF_BACKUP_REPO nicht erreichbar oder Passwort falsch."

    rm -rf "$staging"; mkdir -p "$staging/config"; chmod 700 "$staging"
    if [ "$in_window" != --in-window ]; then
        ad_health_internal 1 && was_running=1
        if [ "$was_running" = 1 ]; then
            step "Wartungsfenster: Oberfläche und Worker anhalten"
            ad_app_stop
            # Restart on every exit path, including failures (die -> exit).
            trap _backup_window_end EXIT
        fi
    fi
    ad_db_start

    step "Datenbank sichern"
    dump="$staging/db.dump"
    if ! ad_db_dump "$dump" || [ ! -s "$dump" ]; then
        _backup_status failed "" "Datenbankdump fehlgeschlagen"
        die "$EX_ERROR" "Datenbankdump fehlgeschlagen – keine Sicherung erstellt."
    fi
    install -m 600 "$JF_APP_ENV" "$staging/config/app.env"
    install -m 600 "$JF_CONF" "$staging/config/jfctl.conf"
    [ -f "$JF_ETC/maintenance.conf" ] && install -m 600 "$JF_ETC/maintenance.conf" "$staging/config/maintenance.conf"

    local uploads files bytes
    uploads=$(ad_uploads_dir)
    mkdir -p "$uploads"
    files=$(find "$uploads" -type f | wc -l)
    bytes=$(du -sb "$uploads" | awk '{print $1}')
    jq -n --argjson format "$BACKUP_FORMAT" --arg instance "$JF_INSTANCE" --arg created "$(_ts)" \
        --arg version "${JF_VERSION#v}" --arg mode "$JF_MODE" --arg kind "$kind" --arg reason "$reason" \
        --argjson pg "$(ad_pg_major)" --arg data_dir "$JF_DATA_DIR" \
        --arg dump_sha "$(sha256sum "$dump" | awk '{print $1}')" --argjson dump_bytes "$(stat -c %s "$dump")" \
        --argjson files "${files:-0}" --argjson bytes "${bytes:-0}" \
        '{format: $format, product: "jf-manager", instance: $instance, created: $created,
          app_version: $version, mode: $mode, kind: $kind, reason: $reason, postgres_major: $pg,
          data_dir: $data_dir, db_dump: {file: "db.dump", sha256: $dump_sha, bytes: $dump_bytes},
          uploads: {files: $files, bytes: $bytes}}' >"$staging/manifest.json"

    step "Verschlüsselte Sicherung schreiben ($JF_BACKUP_REPO)"
    if ! out=$(restic backup --json --quiet --host "$JF_INSTANCE" \
            --tag jf-manager --tag "kind=$kind" --tag "version=${JF_VERSION#v}" \
            "$staging" "$uploads" 2>&1); then
        _backup_status failed "" "restic backup fehlgeschlagen"
        rm -rf "$staging"
        die "$EX_ERROR" "Sicherung fehlgeschlagen: $(tail -n 3 <<<"$out")"
    fi
    snap=$(jq -r 'select(.message_type == "summary") | .snapshot_id' <<<"$out" | tail -1)
    if [ -z "$snap" ] || [ "$(jq -r 'select(.message_type == "summary") | .total_files_processed' <<<"$out" | tail -1)" -lt 2 ]; then
        _backup_status failed "" "Sicherung unvollständig"
        rm -rf "$staging"
        die "$EX_ERROR" "Sicherung unvollständig – kein Erfolgsstatus."
    fi
    rm -rf "$staging"
    snap=${snap:0:8}
    _backup_status ok "$snap" "$kind"
    ok "Sicherung $snap erstellt ($kind)"
    BACKUP_LAST_SNAPSHOT=$snap

    if [ "$was_running" = 1 ]; then _backup_window_end; trap - EXIT; fi

    if [ "$kind" = scheduled ] || [ "$kind" = manual ]; then backup_retention || warn "Aufräumen alter Sicherungen fehlgeschlagen (Sicherung $snap ist gültig)"; fi
}

# Retention: regular backups 7 daily / 4 weekly / 6 monthly (restic keeps one
# per period) plus the newest three; safety copies taken before updates and
# restores are kept for 30 days independently, so a later backup on the same
# day never removes them.
backup_retention() {
    restic forget --quiet --group-by host \
        --tag jf-manager,kind=scheduled --tag jf-manager,kind=manual \
        --keep-last 3 --keep-daily "$JF_BACKUP_KEEP_DAILY" --keep-weekly "$JF_BACKUP_KEEP_WEEKLY" \
        --keep-monthly "$JF_BACKUP_KEEP_MONTHLY" >/dev/null &&
    restic forget --quiet --group-by host \
        --tag jf-manager,kind=pre-update --tag jf-manager,kind=pre-restore --tag jf-manager,kind=pre-department-move \
        --keep-within 30d --keep-last 2 >/dev/null &&
    restic prune --quiet >/dev/null
}

backup_list() {
    restic_env
    local json
    json=$(restic snapshots --tag jf-manager --json 2>/dev/null) || die "$EX_PRECHECK" "Repository $JF_BACKUP_REPO nicht lesbar."
    printf '%-10s %-20s %-10s %-12s %s\n' ID "ZEIT (UTC)" VERSION ART HOST
    jq -r 'sort_by(.time) | reverse | .[] | [.short_id, (.time | sub("\\..*"; "")),
          ((.tags // []) | map(select(startswith("version="))) | first // "-" | sub("version="; "")),
          ((.tags // []) | map(select(startswith("kind="))) | first // "-" | sub("kind="; "")),
          .hostname] | @tsv' <<<"$json" | while IFS=$'\t' read -r id time version kind host; do
        printf '%-10s %-20s %-10s %-12s %s\n' "$id" "$time" "$version" "$kind" "$host"
    done
}

# backup_fetch ID TARGET -> restores the snapshot into TARGET and sets
# FETCH_STAGING / FETCH_UPLOADS / FETCH_MANIFEST (paths inside TARGET).
backup_fetch() {
    local id=$1 target=$2
    FETCH_FROM_DIR=0
    if [[ $id == dir:* ]]; then
        # Export directory in the backup layout (jfctl migrate legacy-compose).
        local dir=${id#dir:}
        FETCH_MANIFEST="$dir/backup-staging/manifest.json"
        [ -f "$FETCH_MANIFEST" ] || { err "$dir enthält kein Exportmanifest"; return 1; }
        FETCH_STAGING="$dir/backup-staging"; FETCH_UPLOADS="$dir/uploads"; FETCH_FROM_DIR=1
        return 0
    fi
    restic_env
    rm -rf "$target"; mkdir -p "$target"; chmod 700 "$target"
    restic restore "$id" --target "$target" --tag jf-manager >/dev/null 2>&1 ||
        { err "Sicherung $id nicht lesbar (ID, Passwort oder Repository prüfen)"; return 1; }
    FETCH_MANIFEST=$(find "$target" -path '*/backup-staging/manifest.json' -print -quit)
    [ -n "$FETCH_MANIFEST" ] || { err "Sicherung $id enthält kein JF-Manager-Manifest"; return 1; }
    FETCH_STAGING=$(dirname "$FETCH_MANIFEST")
    FETCH_UPLOADS="$target$(jq -r .data_dir "$FETCH_MANIFEST")/uploads"
    [ -d "$FETCH_UPLOADS" ] || FETCH_UPLOADS=$(find "$target" -type d -name uploads -not -path '*/backup-staging/*' -print -quit)
}

# Checks a fetched backup: format, product, dump checksum and dump readability.
backup_check_fetched() {
    local m=$FETCH_MANIFEST dump
    [ "$(jq -r .product "$m")" = jf-manager ] || { err "Kein JF-Manager-Backup"; return 1; }
    [ "$(jq -r .format "$m")" -le "$BACKUP_FORMAT" ] || { err "Backupformat $(jq -r .format "$m") ist neuer als dieses jfctl"; return 1; }
    dump="$FETCH_STAGING/$(jq -r .db_dump.file "$m")"
    [ "$(sha256sum "$dump" | awk '{print $1}')" = "$(jq -r .db_dump.sha256 "$m")" ] || { err "Prüfsumme des Datenbankdumps stimmt nicht"; return 1; }
    pg_dump_list "$dump" >/dev/null || { err "Datenbankdump ist nicht lesbar"; return 1; }
    [ -f "$FETCH_STAGING/config/app.env" ] && kv_get "$FETCH_STAGING/config/app.env" FIELD_ENCRYPTION_KEY >/dev/null ||
        { err "Sicherung enthält keine Anwendungsschlüssel"; return 1; }
    if [ -n "$FETCH_UPLOADS" ] && [ -d "$FETCH_UPLOADS" ]; then
        local n; n=$(find "$FETCH_UPLOADS" -type f | wc -l)
        [ "$n" -ge "$(jq -r .uploads.files "$m")" ] || { err "Uploads unvollständig ($n von $(jq -r .uploads.files "$m") Dateien)"; return 1; }
    elif [ "$(jq -r .uploads.files "$m")" -gt 0 ]; then
        err "Uploads fehlen in der Sicherung"; return 1
    fi
    return 0
}

# pg_restore --list via the database container/host tools (dump readability).
pg_dump_list() {
    if [ "$JF_MODE" = compose ]; then dc exec -T db pg_restore --list <"$1"
    else pg_restore --list "$1"; fi
}

# backup_in_window KIND REASON -> separate jfctl process (own errexit, no lock:
# the caller holds it); sets BACKUP_LAST_SNAPSHOT on success.
backup_in_window() {
    BACKUP_LAST_SNAPSHOT=""
    JFCTL_INTERNAL=1 "$JFCTL_SELF" --non-interactive __backup "$1" "$2" || return 1
    [ "$(jq -r .status "$JF_STATE_DIR/last-backup.json")" = ok ] || return 1
    BACKUP_LAST_SNAPSHOT=$(jq -r .snapshot "$JF_STATE_DIR/last-backup.json")
}

cmd___backup() {
    [ -n "${JFCTL_INTERNAL:-}" ] || die "$EX_USAGE" "Interner Befehl."
    require_installed; load_adapter
    backup_create "$1" "$2" --in-window
}

cmd_backup() {
    require_installed; load_adapter
    local sub=${1:-list}; shift || true
    case $sub in
        create)
            need_root
            local kind=manual
            [ "${1:-}" = --scheduled ] && kind=scheduled
            if [ "$kind" = scheduled ]; then
                exec 9>"$JF_LOCK_FILE"
                flock -n 9 || { log "Geplante Sicherung übersprungen: anderer jfctl-Vorgang läuft"; return 0; }
            else
                acquire_lock "backup create"
            fi
            backup_create "$kind" "jfctl backup create" ;;
        list) backup_list ;;
        verify)
            need_root
            local id=${1:-latest} tmp
            acquire_lock "backup verify"
            step "Repository prüfen"
            restic_env
            restic check --read-data-subset=10% >/dev/null 2>&1 || die "$EX_VERIFY" "restic check meldet Fehler im Repository."
            ok "Repository konsistent (10 % der Daten gelesen)"
            step "Sicherung $id vollständig auslesen und prüfen"
            tmp="$JF_DATA_DIR/verify-staging"
            backup_fetch "$id" "$tmp" || { rm -rf "$tmp"; die "$EX_VERIFY" "Sicherung $id nicht lesbar."; }
            if backup_check_fetched; then
                ok "Sicherung $id gültig: Version $(jq -r .app_version "$FETCH_MANIFEST"), $(jq -r .created "$FETCH_MANIFEST"), $(jq -r .uploads.files "$FETCH_MANIFEST") Uploaddateien"
                rm -rf "$tmp"
            else
                rm -rf "$tmp"; die "$EX_VERIFY" "Sicherung $id ist beschädigt oder unvollständig."
            fi ;;
        *) die "$EX_USAGE" "jfctl backup create | list | verify [ID]" ;;
    esac
}
