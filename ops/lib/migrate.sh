# shellcheck shell=bash
# Takeover of legacy installations (OPS-05.1): docker-compose.yml from the
# project root, Portainer and Synology stacks. All of them use the container
# names jf_manager_db / jf_manager_backend / jf_manager_frontend.
#
#   1. jfctl migrate legacy-compose --from DIR   exports DB, uploads and keys
#      into an import directory in the standard backup layout and stops the
#      old stack.
#   2. jfctl install (Aktion "import", JF_IMPORT_DIR=…) installs the new
#      version and restores the export with the regular restore code path.
# A logical dump moves the data from PostgreSQL 15 to 17 on the way.

# Legacy .env keys that are infrastructure of the old stack, not application settings.
LEGACY_SKIP_KEYS='^(POSTGRES_.*|BACKUP_.*|VITE_.*|HTTP_PORT|HTTPS_PORT|BUILD_DATE|VCS_REF|DJANGO_MANAGEPY_MIGRATE|DJANGO_ADMIN_PASSWORD|DJANGO_ADMIN_EMAIL|DATABASE_URL|REDIS_URL|COMPOSE_.*|IMAGE_TAG|STATIC_ROOT|MEDIA_ROOT|STATIC_URL|MEDIA_URL)$'

_legacy_kv() { # file key -> value of KEY=VALUE, KEY="VALUE" or KEY='VALUE'
    local line
    line=$(grep -E "^[[:space:]]*(export[[:space:]]+)?$2=" "$1" | tail -1) || return 1
    line=${line#*=}
    line=${line%$'\r'}
    if [[ $line == \"*\" ]] || [[ $line == \'*\' ]]; then line=${line:1:${#line}-2}; fi
    printf '%s' "$line"
}

cmd_migrate() {
    local sub=${1:-}; shift || true
    case $sub in
        legacy-compose) migrate_legacy_compose "$@" ;;
        *) die "$EX_USAGE" "jfctl migrate legacy-compose --from VERZEICHNIS [--env-file DATEI] [--out VERZEICHNIS] [--keep-running]" ;;
    esac
}

migrate_legacy_compose() {
    need_root
    local from="" env_file="" out="" keep_running=0 db=jf_manager_db backend=jf_manager_backend frontend=jf_manager_frontend
    while [ $# -gt 0 ]; do
        case $1 in
            --from) from=$2; shift 2 ;;
            --env-file) env_file=$2; shift 2 ;;
            --out) out=$2; shift 2 ;;
            --keep-running) keep_running=1; shift ;;
            --db-container) db=$2; shift 2 ;;
            --backend-container) backend=$2; shift 2 ;;
            *) die "$EX_USAGE" "Unbekannte Option: $1" ;;
        esac
    done
    [ -n "$from" ] || die "$EX_USAGE" "--from VERZEICHNIS der alten Installation fehlt."
    : "${env_file:=$from/.env}"
    [ -f "$env_file" ] || die "$EX_PRECHECK" "Umgebungsdatei $env_file fehlt (bei Portainer: Stack-Variablen als Datei exportieren, --env-file)."
    : "${out:=${JFCTL_IMPORT_BASE:-/var/lib/jf-manager/import}/legacy-$(date +%Y%m%d-%H%M%S)}"
    acquire_lock "migrate legacy-compose"
    have docker || die "$EX_PRECHECK" "Docker fehlt – die alte Installation läuft nicht auf diesem Host."

    step "Vorabprüfung der alten Installation"
    local pg_user pg_db secret field uploads_src pg_major key
    pg_user=$(_legacy_kv "$env_file" POSTGRES_USER || echo jf_manager)
    pg_db=$(_legacy_kv "$env_file" POSTGRES_DB || echo jf_manager_backend)
    secret=$(_legacy_kv "$env_file" DJANGO_SECRET_KEY || true)
    field=$(_legacy_kv "$env_file" FIELD_ENCRYPTION_KEY || true)
    register_secret "$secret"; register_secret "$field"
    register_secret "$(_legacy_kv "$env_file" POSTGRES_PASSWORD || true)"
    register_secret "$(_legacy_kv "$env_file" EMAIL_HOST_PASSWORD || true)"
    [ -n "$secret" ] || die "$EX_PRECHECK" "DJANGO_SECRET_KEY fehlt in $env_file."
    if [ -z "$field" ] || [[ $field == CHANGE_ME* ]]; then
        die "$EX_PRECHECK" "FIELD_ENCRYPTION_KEY fehlt in $env_file. Ohne den bisherigen Schlüssel sind verschlüsselte Zugangsdaten nicht lesbar (docs/security-upgrade.md)."
    fi
    [ "$(docker inspect -f '{{.State.Running}}' "$db" 2>/dev/null)" = true ] ||
        die "$EX_PRECHECK" "Datenbankcontainer $db läuft nicht (alte Installation zuerst starten)."
    pg_major=$(docker exec "$db" psql -U "$pg_user" -d "$pg_db" -tAc 'SHOW server_version_num' | awk '{print int($1/10000)}') ||
        die "$EX_PRECHECK" "Anmeldung an der alten Datenbank fehlgeschlagen ($pg_user/$pg_db)."
    ok "Alte Datenbank: PostgreSQL $pg_major, Datenbank $pg_db"
    uploads_src=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/uploads"}}{{.Source}}{{end}}{{end}}' "$backend" 2>/dev/null || true)
    if [ -n "$uploads_src" ] && [ -d "$uploads_src" ]; then ok "Uploads: $uploads_src"
    else warn "Kein Uploadverzeichnis am Container $backend gefunden – es werden keine Dateien übernommen"; uploads_src=""; fi
    mkdir -p "$(dirname "$out")"
    local free need
    free=$(free_bytes "$(dirname "$out")")
    need=$(( $(docker exec "$db" psql -U "$pg_user" -d "$pg_db" -tAc "SELECT pg_database_size(current_database())") + $(du -sb "${uploads_src:-/dev/null}" 2>/dev/null | awk '{print $1+0}') ))
    [ "$free" -gt "$need" ] || die "$EX_PRECHECK" "Zu wenig Speicher für den Export ($(human_bytes "$free") frei, $(human_bytes "$need") nötig)."

    if [ "$keep_running" = 0 ]; then
        confirm_yes "Oberfläche und Backend der alten Installation werden angehalten (die Datenbank läuft bis zum Ende des Exports). Fortfahren?" ||
            die "$EX_ABORTED" "Abgebrochen – nichts verändert."
    fi

    step "Export nach $out"
    mkdir -p "$out/backup-staging/config" "$out/uploads"; chmod 700 "$out"
    if [ "$keep_running" = 0 ]; then
        docker stop "$frontend" "$backend" >/dev/null 2>&1 || true
        docker ps --format '{{.Names}}' | grep -E '^(.*push-worker.*|jf_manager_worker)$' | xargs -r docker stop >/dev/null 2>&1 || true
    fi
    docker exec "$db" pg_dump -U "$pg_user" -d "$pg_db" -Fc --no-owner --no-acl >"$out/backup-staging/db.dump" ||
        die "$EX_ERROR" "Datenbankexport fehlgeschlagen."
    [ -s "$out/backup-staging/db.dump" ] || die "$EX_ERROR" "Datenbankexport ist leer."
    if [ -n "$uploads_src" ]; then cp -a "$uploads_src/." "$out/uploads/"; fi

    # Application settings of the old stack, in the shared KEY=VALUE syntax.
    local app="$out/backup-staging/config/app.env" value
    install -m 600 /dev/null "$app"
    while IFS= read -r key; do
        [[ $key =~ $LEGACY_SKIP_KEYS ]] && continue
        value=$(_legacy_kv "$env_file" "$key") || continue
        [ -n "$value" ] || continue
        kv_set "$app" "$key" "$value" 2>/dev/null || warn "$key nicht übernommen (Hochkomma im Wert) – nach dem Import per jfctl config set setzen"
    done < <(grep -oE '^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=' "$env_file" | sed -E 's/^[[:space:]]*(export[[:space:]]+)?//; s/=$//' | sort -u)
    kv_set "$app" DEBUG False

    local files bytes
    files=$(find "$out/uploads" -type f | wc -l); bytes=$(du -sb "$out/uploads" | awk '{print $1}')
    jq -n --arg created "$(_ts)" --argjson pg "$pg_major" --arg from "$from" \
        --arg sha "$(sha256sum "$out/backup-staging/db.dump" | awk '{print $1}')" \
        --argjson dump_bytes "$(stat -c %s "$out/backup-staging/db.dump")" --argjson files "$files" --argjson bytes "$bytes" \
        '{format: 1, product: "jf-manager", instance: "legacy", created: $created, app_version: "0.0.0",
          mode: "legacy-compose", kind: "legacy-import", reason: $from, postgres_major: $pg, data_dir: "",
          db_dump: {file: "db.dump", sha256: $sha, bytes: $dump_bytes}, uploads: {files: $files, bytes: $bytes}}' \
        >"$out/backup-staging/manifest.json"
    if [ "$keep_running" = 0 ]; then docker stop "$db" "${db%_db}_redis" >/dev/null 2>&1 || true; fi
    ok "Export abgeschlossen: $(stat -c %s "$out/backup-staging/db.dump" | numfmt --to=iec) Datenbank, $files Uploaddateien"
    _log_file "AUDIT legacy export from=$from out=$out"
    cat <<EOF

Nächster Schritt: neue Installation mit Übernahme dieses Exports
  sudo jfctl install          (Aktion "import", Verzeichnis: $out)
oder mit Antwortdatei:  JF_ACTION=import  JF_IMPORT_DIR=$out

Der Export enthält Schlüssel und personenbezogene Daten (Rechte 0700). Nach
erfolgreicher Übernahme und erster Sicherung löschen. Die alte Installation
bleibt unverändert gestoppt und kann bei Bedarf wieder gestartet werden.
EOF
}
