# shellcheck shell=bash
# Recurring maintenance as systemd timers on the host, identical for Compose
# and native installs. Each timer runs "jfctl maintenance run <task>", which
# runs the Django management command through the active adapter.

# name|OnCalendar|management command|enabled by default|description
MAINT_TASKS=(
    "sessions|*-*-* 03:10:00|clearsessions|1|Abgelaufene Sitzungen und Geräteeinträge entfernen (SEC-07)"
    "export-audits|*-*-* 03:20:00|purge_export_audits|1|Abgelaufene Export-Auditeinträge löschen (SEC-08)"
    "booking-requests|*-*-* 03:30:00|purge_booking_requests|1|Gespeicherte Buchungsantworten nach Aufbewahrungsfrist löschen (SEC-09)"
    "sync-due|*:0/5|run_due_sync_jobs|1|Fällige Synchronisationsaufträge an den Worker übergeben"
    "portal-access|*-*-* 03:40:00|portal_access_lifecycle|1|Elternzugänge nach Volljährigkeit der Kinder beenden (PORTAL-01.4)"
    "order-reminders|Mon *-*-* 07:00:00|send_pending_reminders|0|Erinnerungs-E-Mails für offene Bestellungen (optional)"
)

_maint_field() { # task field-index
    local entry
    for entry in "${MAINT_TASKS[@]}"; do
        if [ "${entry%%|*}" = "$1" ]; then cut -d'|' -f"$2" <<<"$entry"; return 0; fi
    done
    return 1
}

_maint_enabled() { # task -> 0 when enabled (state file overrides the default)
    local override
    override=$(kv_get "$JF_ETC/maintenance.conf" "TASK_${1//-/_}" 2>/dev/null || true)
    [ "${override:-$(_maint_field "$1" 4)}" = 1 ]
}

maintenance_install_timers() {
    local entry name schedule unit sbin=${JFCTL_SBIN:-/usr/local/sbin/jfctl}
    { have systemctl && { [ -d /run/systemd/system ] || [ -n "${JFCTL_ASSUME_SYSTEMD:-}" ]; }; } ||
        { warn "systemd läuft nicht – Wartungstimer nicht eingerichtet"; return 0; }
    cat >"$SYSTEMD_DIR/jf-manager-maint@.service" <<EOF
[Unit]
Description=JF-Manager Wartung: %i
After=network-online.target

[Service]
Type=oneshot
ExecStart=$sbin --non-interactive maintenance run %i
SyslogIdentifier=jf-manager-maint
EOF
    cat >"$SYSTEMD_DIR/jf-manager-backup.service" <<EOF
[Unit]
Description=JF-Manager Sicherung (Restic)
After=network-online.target

[Service]
Type=oneshot
ExecStart=$sbin --non-interactive backup create --scheduled
SyslogIdentifier=jf-manager-backup
TimeoutStartSec=6h
EOF
    cat >"$SYSTEMD_DIR/jf-manager-backup.timer" <<EOF
[Unit]
Description=JF-Manager tägliche Sicherung

[Timer]
OnCalendar=$JF_BACKUP_SCHEDULE
RandomizedDelaySec=10min
Persistent=true

[Install]
WantedBy=timers.target
EOF
    for entry in "${MAINT_TASKS[@]}"; do
        name=${entry%%|*}
        schedule=$(_maint_field "$name" 2)
        unit="jf-manager-maint-$name.timer"
        cat >"$SYSTEMD_DIR/$unit" <<EOF
[Unit]
Description=JF-Manager Wartung: $name

[Timer]
OnCalendar=$schedule
Persistent=true
Unit=jf-manager-maint@$name.service

[Install]
WantedBy=timers.target
EOF
    done
    systemctl daemon-reload
    systemctl enable --now jf-manager-backup.timer >/dev/null 2>&1
    for entry in "${MAINT_TASKS[@]}"; do
        name=${entry%%|*}
        if _maint_enabled "$name"; then
            systemctl enable --now "jf-manager-maint-$name.timer" >/dev/null 2>&1
        else
            systemctl disable --now "jf-manager-maint-$name.timer" >/dev/null 2>&1 || true
        fi
    done
    ok "Wartungs- und Backup-Timer eingerichtet"
}

cmd_maintenance() {
    require_installed
    local sub=${1:-list} task=${2:-} cmd
    case $sub in
        list)
            local entry name
            printf '%-18s %-6s %-22s %s\n' AUFGABE AKTIV ZEITPLAN BESCHREIBUNG
            for entry in "${MAINT_TASKS[@]}"; do
                name=${entry%%|*}
                printf '%-18s %-6s %-22s %s\n' "$name" "$(_maint_enabled "$name" && echo ja || echo nein)" \
                    "$(_maint_field "$name" 2)" "$(_maint_field "$name" 5)"
            done
            printf '%-18s %-6s %-22s %s\n' backup ja "$JF_BACKUP_SCHEDULE" "Verschlüsselte Sicherung (jfctl backup create)" ;;
        run)
            cmd=$(_maint_field "$task" 3) || die "$EX_USAGE" "Unbekannte Aufgabe: ${task:-–} (jfctl maintenance list)"
            load_adapter
            # Never interfere with updates/restores; the next run catches up.
            exec 9>"$JF_LOCK_FILE"
            if ! flock -n 9; then log "Wartung $task übersprungen: anderer jfctl-Vorgang läuft"; return 0; fi
            if [ "$task" = sync-due ] && workers_held; then log "Wartung $task übersprungen: Worker angehalten"; return 0; fi
            if ad_manage "$cmd"; then ok "Wartung $task ($cmd) erledigt"; else die "$EX_ERROR" "Wartung $task ($cmd) fehlgeschlagen"; fi ;;
        enable|disable)
            need_root
            _maint_field "$task" 1 >/dev/null || die "$EX_USAGE" "Unbekannte Aufgabe: ${task:-–}"
            [ -f "$JF_ETC/maintenance.conf" ] || install -m 600 /dev/null "$JF_ETC/maintenance.conf"
            kv_set "$JF_ETC/maintenance.conf" "TASK_${task//-/_}" "$([ "$sub" = enable ] && echo 1 || echo 0)"
            maintenance_install_timers ;;
        install-timers) need_root; maintenance_install_timers ;;
        *) die "$EX_USAGE" "jfctl maintenance list | run AUFGABE | enable AUFGABE | disable AUFGABE" ;;
    esac
}

SYSTEMD_DIR=${JFCTL_SYSTEMD_DIR:-/etc/systemd/system}
