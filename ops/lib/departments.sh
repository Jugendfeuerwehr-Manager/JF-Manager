# shellcheck shell=bash
# Run the bundled, tested Python engine in the installed Django environment.
# This works with Compose/native and does not replace application images.
_transfer_python() {
    local payload=$1 engine="$JFCTL_HOME/tools/department_transfer.py"
    [ -r "$engine" ] || die "$EX_PRECHECK" "Umzugswerkzeug fehlt: $engine"
    ad_manage shell --no-imports --command "$(cat "$engine")
print(json.dumps($payload, ensure_ascii=False))"
}

_transfer_reopen() {
    [ "${_TRANSFER_WAS_RUNNING:-1}" = 1 ] && _backup_window_end
    return 0
}

cmd_departments() {
    need_root; require_installed; load_adapter
    local sub=${1:-list}; shift || true
    case $sub in
        list)
            [ $# -eq 0 ] || die "$EX_USAGE" "jfctl departments list"
            _transfer_python 'list_departments()'
            return ;;
        move) ;;
        *) die "$EX_USAGE" "jfctl departments list | move --from global|KÜRZEL --to global|KÜRZEL --areas KOMMALISTE [--create-target NAME] [--apply --confirm INSTANZ]" ;;
    esac
    local source="" target="" areas="" name="" apply=0 confirm="" plan payload digest tmp
    while [ $# -gt 0 ]; do
        case $1 in
            --from|--to|--areas|--create-target|--confirm)
                [ $# -ge 2 ] || die "$EX_USAGE" "Wert für $1 fehlt"
                case $1 in
                    --from) source=$2 ;; --to) target=$2 ;; --areas) areas=$2 ;;
                    --create-target) name=$2 ;; --confirm) confirm=$2 ;;
                esac
                shift 2 ;;
            --apply) apply=1; shift ;;
            *) die "$EX_USAGE" "Unbekannte Option $1" ;;
        esac
    done
    [ -n "$source" ] && [ -n "$target" ] && [ -n "$areas" ] || die "$EX_USAGE" "Quelle, Ziel und explizite Bereichsauswahl fehlen."
    payload="run_transfer(source=$(json_str "$source"), target=$(json_str "$target"), areas=$(json_str "$areas"), create_name=$(json_str "$name"))"
    acquire_lock "departments move"
    plan=$(_transfer_python "$payload") || die "$EX_PRECHECK" "Vorschau fehlgeschlagen – nichts geändert."
    jq . <<<"$plan" || die "$EX_PRECHECK" "Ungültige Vorschau – nichts geändert."
    [ "$(jq '.conflicts | length' <<<"$plan")" = 0 ] || die "$EX_PRECHECK" "Abhängigkeiten zuerst klären (siehe Vorschau)."
    [ "$apply" = 1 ] || { ok "Nur Vorschau. Ausführen mit --apply --confirm $JF_INSTANCE"; return 0; }
    [ "$confirm" = "$JF_INSTANCE" ] || die "$EX_USAGE" "Ausführung verlangt --confirm $JF_INSTANCE (auch mit --yes)."
    digest=$(jq -r .fingerprint <<<"$plan")
    [[ $digest =~ ^[a-f0-9]{64}$ ]] || die "$EX_PRECHECK" "Vorschau ohne gültigen Fingerprint."

    _TRANSFER_WAS_RUNNING=0
    ad_health_internal 1 && _TRANSFER_WAS_RUNNING=1
    step "Schreibzugriffe und Hintergrundaufträge anhalten"
    # Install the recovery trap before the first stop so partial stop failures
    # also return to the previous operating state. Explicitly held workers stay held.
    trap _transfer_reopen EXIT
    ad_entry_stop
    ad_app_stop
    step "Vollständige Vorabsicherung erstellen"
    backup_in_window pre-department-move "Abteilungsumzug $source -> $target" || die "$EX_ERROR" "Sicherung fehlgeschlagen – keine Daten verschoben."
    step "Vorabsicherung vollständig auslesen und prüfen"
    tmp="$JF_DATA_DIR/department-backup-verify"
    if ! backup_fetch "$BACKUP_LAST_SNAPSHOT" "$tmp" || ! backup_check_fetched; then
        rm -rf "$tmp"
        die "$EX_VERIFY" "Vorabsicherung nicht verifizierbar – keine Daten verschoben."
    fi
    rm -rf "$tmp"
    # The engine revalidates every dependency and the preview fingerprint under
    # transaction/table locks. Failure rolls back all data, including target creation.
    step "Abteilungsdaten atomar verschieben"
    plan=$(_transfer_python "${payload%)} , apply=True, expect=$(json_str "$digest"))") || die "$EX_ERROR" "Umzug zurückgerollt – Vorabsicherung $BACKUP_LAST_SNAPSHOT bleibt erhalten."
    jq . <<<"$plan"
    _log_file "AUDIT departments move $source -> $target areas=$areas snapshot=$BACKUP_LAST_SNAPSHOT fingerprint=$digest"
    _transfer_reopen
    trap - EXIT
    [ "$_TRANSFER_WAS_RUNNING" = 0 ] || ad_health_internal 90 || die "$EX_VERIFY" "Daten verschoben, Anwendung startet nicht; jfctl doctor/restore prüfen. Sicherung: $BACKUP_LAST_SNAPSHOT"
    write_ops_status
    ok "Umzug abgeschlossen. Vorabsicherung: $BACKUP_LAST_SNAPSHOT"
}
