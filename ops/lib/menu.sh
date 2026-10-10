# shellcheck shell=bash
# Interactive menu (jfctl without arguments). Every entry calls the same
# command as the scripted form, so the menu adds no separate logic.

_menu_run() { # runs a command in a subshell so "die" returns to the menu
    ( "$@" ) || printf '\n(Rückgabecode %s)\n' "$?"
    printf '\nWeiter mit Eingabetaste … '
    read -r _ || true
}

cmd_menu() {
    local choice installed=0
    conf_load 2>/dev/null && [ -n "${JF_MODE:-}" ] && installed=1
    while true; do
        printf '\n\033[1mJF-Manager – Betrieb\033[0m'
        if [ "$installed" = 1 ]; then
            printf '  (%s, Version %s, %s)\n\n' "$JF_INSTANCE" "${JF_VERSION:-?}" "$JF_MODE"
            cat <<'EOF'
  1) Status anzeigen              6) Sicherungen anzeigen
  2) Installation prüfen (doctor) 7) Sicherung prüfen
  3) Starten / Stoppen / Neustart 8) Wiederherstellen
  4) Protokolle anzeigen          9) Update auf neue Version
  5) Sicherung jetzt erstellen   10) Konfiguration anzeigen
                                 11) Administratorzugang wiederherstellen
                                 12) Zwei-Faktor-Anmeldung zurücksetzen
                                 13) Daten in andere Abteilung verschieben
  q) Beenden
EOF
        else
            printf '  (nicht installiert)\n\n'
            cat <<'EOF'
  1) Installieren oder aus Sicherung wiederherstellen
  2) Alte Compose-Installation übernehmen
  q) Beenden
EOF
        fi
        printf '\nAuswahl: '
        IFS= read -r choice || return 0
        if [ "$installed" = 0 ]; then
            case $choice in
                1) _menu_run cmd_install; conf_load 2>/dev/null && [ -n "${JF_MODE:-}" ] && installed=1 ;;
                2) local from; ask from "Verzeichnis der alten Installation (mit docker-compose.yml)" "/opt/jf-manager-alt"
                   _menu_run cmd_migrate legacy-compose --from "$from" ;;
                q|Q) return 0 ;;
            esac
            continue
        fi
        case $choice in
            1) _menu_run cmd_status ;;
            2) _menu_run cmd_doctor ;;
            3) local action; ask action "start, stop oder restart" "restart"
               case $action in start|stop|restart) _menu_run "cmd_$action" ;; *) echo "Unbekannt: $action" ;; esac ;;
            4) local svc; ask svc "Dienst (leer = alle, jfctl = jfctl-Protokoll)" ""
               # shellcheck disable=SC2086
               _menu_run cmd_logs $svc ;;
            5) _menu_run cmd_backup create ;;
            6) _menu_run cmd_backup list ;;
            7) local id; ask id "Sicherungs-ID (leer = neueste)" "latest"; _menu_run cmd_backup verify "$id" ;;
            8) local id; ask id "Sicherungs-ID" ""; [ -n "$id" ] && _menu_run cmd_restore "$id" ;;
            9) local v; ask v "Zielversion (z. B. 1.4.0)" ""; [ -n "$v" ] && _menu_run cmd_update --version "$v" ;;
            10) _menu_run cmd_config show ;;
            11) _menu_run cmd_admin recover ;;
            12) _menu_run cmd_admin reset-mfa ;;
            13) _menu_run cmd_departments list
                local from to areas target_name execute
                ask from "Quellkürzel (global = ohne Abteilung)" "global"
                ask to "Zielkürzel (oder global)" "jugendfeuerwehr"
                ask target_name "Name für neues Ziel (leer bei bestehendem Ziel)" ""
                printf 'Bereiche: members,groups,lists,events,services,training,templates,email,inventory,orders\n'
                ask areas "Zu verschiebende Bereiche als Kommaliste" "members,groups,lists,events,services,training,templates,email"
                _menu_run cmd_departments move --from "$from" --to "$to" --areas "$areas" --create-target "$target_name"
                ask execute "Ausführen? Zur Bestätigung Instanznamen eingeben (leer = abbrechen)" ""
                [ "$execute" = "$JF_INSTANCE" ] && _menu_run cmd_departments move --from "$from" --to "$to" --areas "$areas" --create-target "$target_name" --apply --confirm "$execute"
                ;;
            q|Q) return 0 ;;
            *) echo "Unbekannte Auswahl" ;;
        esac
    done
}
