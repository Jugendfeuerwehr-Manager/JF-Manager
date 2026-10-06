# shellcheck shell=bash
# Update (OPS-04.3):
#   1. check target version and compatibility      (nothing changed)
#   2. load and verify artifacts, prepare runtime  (no downtime)
#   3. maintenance: close entry, stop workers, full backup
#   4. switch release, run migrations
#   5. verify backend, workers and checks while users are still locked out
#   6. release (open entry)
# Failure before migrations: previous release again. Failure at/after
# migrations: previous release plus the pre-update database from step 3.
# Automatic rollback happens only before step 6, so no user writes are lost.

_update_state() { printf '%s' "$JF_STATE_DIR/update.state"; }
_update_stage() { state_dir >/dev/null; [ -f "$(_update_state)" ] || install -m 600 /dev/null "$(_update_state)"; kv_set "$(_update_state)" STAGE "$1"; kv_set "$(_update_state)" UPDATED "$(_ts)"; }

_RESTORE_DB_ONLY=0

_update_rollback() { # reason
    local prev snap stage
    stage=$(kv_get "$(_update_state)" STAGE || true)
    prev=$(kv_get "$(_update_state)" PREVIOUS_VERSION || true)
    snap=$(kv_get "$(_update_state)" PRE_UPDATE_SNAPSHOT || true)
    err "Update fehlgeschlagen ($1) in Stufe $stage – stelle Version $prev wieder her"
    ad_app_stop >/dev/null 2>&1 || true
    if [ "$stage" = migrate ] || [ "$stage" = verify ]; then
        step "Datenbankstand vor dem Update aus Sicherung $snap zurückholen"
        local staging="$JF_DATA_DIR/restore-staging"
        if backup_fetch "$snap" "$staging" && backup_check_fetched; then
            RESTORE_STAGING=$FETCH_STAGING
            if _restore_db_prepare && _restore_db_activate; then
                ok "Datenbank auf Stand vor dem Update zurückgesetzt"
            else
                rm -rf "$staging"; _update_stage rollback-failed
                die "$EX_ERROR" "Rücksetzen der Datenbank fehlgeschlagen. Anwendung bleibt gesperrt. Manuell: jfctl restore $snap"
            fi
        else
            rm -rf "$staging"; _update_stage rollback-failed
            die "$EX_ERROR" "Sicherung $snap nicht lesbar. Anwendung bleibt gesperrt. Manuell: jfctl restore $snap"
        fi
        rm -rf "$staging"
    fi
    JF_VERSION=$prev
    switch_current "$prev"
    ad_activate_release "$prev"
    conf_save
    ad_app_start
    if ad_health_internal 90; then
        ad_entry_start
        _update_stage rolled-back
        kv_set "$(_update_state)" FAILED_REASON "$1"
        write_ops_status
        die "$EX_ROLLEDBACK" "Update zurückgerollt; Version $prev läuft wieder."
    fi
    _update_stage rollback-failed
    die "$EX_ERROR" "Version $prev startet nach dem Rückrollen nicht. Anwendung bleibt gesperrt (jfctl logs, jfctl restore $snap)."
}

cmd_update() {
    need_root; require_installed; load_adapter
    local target="" release_dir="" current cmp rdir manifest
    while [ $# -gt 0 ]; do
        case $1 in
            --version) target=${2#v}; shift 2 ;;
            --release-dir) release_dir=$2; shift 2 ;;
            *) die "$EX_USAGE" "Unbekannte Option: $1" ;;
        esac
    done
    [ -n "$target" ] || die "$EX_USAGE" "jfctl update --version X.Y.Z"
    valid_version "$target" || die "$EX_USAGE" "Ungültige Version '$target'. Branches oder Commits werden nicht installiert."
    acquire_lock "update $target"
    current=${JF_VERSION#v}

    step "1/6 Zielversion prüfen"
    if [ -f "$(_update_state)" ]; then
        case "$(kv_get "$(_update_state)" STAGE)" in
            done|rolled-back) ;;
            *) die "$EX_PRECHECK" "Vorheriges Update unvollständig (Stufe $(kv_get "$(_update_state)" STAGE)). Siehe jfctl status / jfctl logs jfctl." ;;
        esac
    fi
    cmp=$(version_cmp "$target" "$current")
    [ "$cmp" = 0 ] && { ok "Version $target ist bereits installiert."; return 0; }
    [ "$cmp" = -1 ] && die "$EX_PRECHECK" "Zielversion $target ist älter als $current. Zurück nur über jfctl restore (Datenbankschema)."
    ok "Wechsel $current → $target"

    step "2/6 Artefakte laden und prüfen"
    rdir=$(release_fetch "$target" "$release_dir")
    manifest="$rdir/release-manifest.json"
    local pg_need pg_have
    pg_need=$(jq -r '.postgres_major // empty' "$manifest")
    ad_db_start; pg_have=$(ad_pg_major)
    if [ -n "$pg_need" ] && [ "$pg_need" != "$pg_have" ]; then
        die "$EX_PRECHECK" "Version $target erwartet PostgreSQL $pg_need, installiert ist $pg_have. Wechsel siehe docs/operations/ops-migration.md."
    fi
    local free; free=$(free_bytes "$JF_DATA_DIR")
    [ "$free" -ge $((3 * 1024 * 1024 * 1024)) ] || die "$EX_PRECHECK" "Zu wenig Speicher für Update und Sicherung ($(human_bytes "$free") frei, 3 GB nötig)."
    release_extract "$rdir" "$target"
    ad_fetch_release "$target" "$JF_OPT/releases/$target/release-manifest.json" ||
        die "$EX_PRECHECK" "Laufzeit für $target konnte nicht vorbereitet werden – nichts geändert."
    ok "Release $target bereit"
    confirm_yes "Update auf $target jetzt durchführen? Die Anwendung ist währenddessen nicht erreichbar." ||
        die "$EX_ABORTED" "Abgebrochen – nichts geändert."

    step "3/6 Wartungsmodus und vollständige Sicherung"
    install -m 600 /dev/null "$(_update_state)"
    kv_set "$(_update_state)" TARGET_VERSION "$target"
    kv_set "$(_update_state)" PREVIOUS_VERSION "$current"
    _update_stage maintenance
    ad_entry_stop
    ad_workers_stop
    trap '_update_rollback "unerwarteter Abbruch"' ERR
    if ! backup_in_window pre-update "vor Update auf $target"; then
        trap - ERR; ad_app_start; ad_entry_start; _update_stage "done"
        die "$EX_ERROR" "Sicherung vor dem Update fehlgeschlagen – Update nicht begonnen, Anwendung wieder freigegeben."
    fi
    kv_set "$(_update_state)" PRE_UPDATE_SNAPSHOT "$BACKUP_LAST_SNAPSHOT"

    step "4/6 Release wechseln und migrieren"
    _update_stage switch
    ad_app_stop
    switch_current "$target"
    ad_activate_release "$target" || _update_rollback "Releasewechsel"
    JF_VERSION=$target
    _update_stage migrate
    ad_manage migrate --noinput || _update_rollback "Migration"

    step "5/6 Prüfen (Anwendung noch gesperrt)"
    _update_stage verify
    ad_app_start
    ad_health_internal 120 || _update_rollback "Backend startet nicht"
    ad_manage check --deploy --fail-level ERROR >/dev/null || _update_rollback "check --deploy"
    ad_manage migrate --check >/dev/null || _update_rollback "offene Migrationen"
    if ! workers_held; then
        sleep 5
        ad_worker_running || _update_rollback "Worker laufen nicht"
    fi
    ok "Backend, Datenbank und Worker geprüft"

    step "6/6 Freigeben"
    trap - ERR
    ad_entry_start
    ad_health_entry 60 || warn "Nginx antwortet nicht – Anwendung läuft, Oberfläche prüfen (jfctl logs frontend)"
    conf_save
    _update_stage "done"
    release_prune
    write_ops_status
    _log_file "AUDIT update $current -> $target snapshot=$BACKUP_LAST_SNAPSHOT"
    ok "Update auf $target abgeschlossen (Sicherung vorher: $BACKUP_LAST_SNAPSHOT)"
}
