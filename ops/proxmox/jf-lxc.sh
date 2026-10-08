#!/usr/bin/env bash
# JF-Manager in a Proxmox VE LXC (OPS-01.3).
# Runs on the Proxmox host. Creates an unprivileged Debian 13 container and
# runs exactly the native installation core (jfctl install --mode native)
# inside it. Installs nothing on the host besides the container template.
#
# Usage: jf-lxc.sh [--release-dir DIR] [--version X.Y.Z] [--answers FILE] [--expert] [--yes]
#   --answers: KEY=VALUE file (root, 0600) with CT_* keys below and the
#              jfctl answer keys (JF_DOMAIN, JF_TLS, …); see docs/operations/ops-install.md
set -Eeuo pipefail
umask 077

SELF_DIR=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
# shellcheck source=../lib/common.sh
. "$SELF_DIR/../lib/common.sh"
JF_LOG_DIR=${JFCTL_LOG_DIR:-/var/log/jf-manager-lxc}

CT_KEYS=(CT_ID CT_HOSTNAME CT_STORAGE CT_TEMPLATE_STORAGE CT_CORES CT_MEMORY CT_SWAP CT_DISK_GB
    CT_BRIDGE CT_IP CT_GATEWAY CT_DNS CT_VLAN)
JF_PASS_KEYS=(JF_VERSION JF_DOMAIN JF_TLS JF_ACME_EMAIL JF_HTTP_BIND JF_TRUSTED_PROXY_ADDRS JF_TIMEZONE
    JF_BACKUP_REPO JF_BACKUP_PASSWORD JF_BACKUP_SCHEDULE JF_ADMIN_USER JF_ADMIN_EMAIL JF_ADMIN_PASSWORD
    JF_ACTION JF_RESTORE_SNAPSHOT JF_INSTANCE EMAIL_HOST EMAIL_PORT EMAIL_HOST_USER EMAIL_HOST_PASSWORD
    EMAIL_USE_TLS DEFAULT_FROM_EMAIL JF_VERIFY_ATTESTATION)

release_dir="" answers="" expert=0
while [ $# -gt 0 ]; do
    case $1 in
        --release-dir) release_dir=$2; shift 2 ;;
        --version) JF_VERSION=${2#v}; shift 2 ;;
        --answers) answers=$2; shift 2 ;;
        --expert) expert=1; shift ;;
        -y|--yes) JF_ASSUME_YES=1; shift ;;
        -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
        *) die "$EX_USAGE" "Unbekannte Option: $1" ;;
    esac
done

need_root

if [ -n "$answers" ]; then
    mode=$(stat -c %a "$answers"); owner=$(stat -c %u "$answers")
    # Same rule as jfctl install: root ownership, relaxed only by the test switch.
    { [ "$owner" = 0 ] || [ -n "${JFCTL_ALLOW_NONROOT:-}" ]; } && [[ $mode =~ ^[0-7]00$ ]] ||
        die "$EX_PRECHECK" "Antwortdatei muss root gehören und 0600 haben."
    kv_validate "$answers" || die "$EX_USAGE" "Antwortdatei fehlerhaft."
    while read -r key; do
        if printf '%s\n' "${CT_KEYS[@]}" "${JF_PASS_KEYS[@]}" | grep -qx "$key"; then
            printf -v "$key" '%s' "$(kv_get "$answers" "$key")"
            case $key in *PASSWORD*) register_secret "${!key}" ;; esac
        else
            die "$EX_USAGE" "Unbekannter Schlüssel in der Antwortdatei: $key"
        fi
    done < <(kv_keys "$answers")
    JF_NONINTERACTIVE=1
fi

# --- Host checks (nothing changed yet) -------------------------------------------
step "Proxmox-Host prüfen"
for tool in pct pveam pvesm pvesh pveversion; do have "$tool" || die "$EX_PRECHECK" "$tool fehlt – dieses Skript läuft nur auf einem Proxmox-VE-Host."; done
pve_version=$(pveversion | sed -n 's#^pve-manager/\([0-9]*\)\..*#\1#p')
if [ "${pve_version:-0}" -ge 9 ]; then ok "Proxmox VE $(pveversion | cut -d/ -f2)"
else warn "Proxmox VE $(pveversion | cut -d/ -f2): Referenzplattform ist Proxmox VE 9.x"; fi
[ "$(dpkg --print-architecture)" = amd64 ] || die "$EX_PRECHECK" "Referenzplattform ist amd64."

# --- Questions -----------------------------------------------------------------------
step "Angaben für den Container"
: "${CT_ID:=$(pvesh get /cluster/nextid 2>/dev/null || echo 200)}"
: "${CT_HOSTNAME:=jf-manager}" "${CT_STORAGE:=local-lvm}" "${CT_TEMPLATE_STORAGE:=local}"
: "${CT_CORES:=2}" "${CT_MEMORY:=2048}" "${CT_SWAP:=512}" "${CT_DISK_GB:=16}"
: "${CT_BRIDGE:=vmbr0}" "${CT_IP:=dhcp}" "${CT_GATEWAY:=}" "${CT_DNS:=}" "${CT_VLAN:=}"
ask CT_ID "CT-ID" "$CT_ID"
ask CT_HOSTNAME "Hostname" "$CT_HOSTNAME"
ask CT_IP "IPv4 (dhcp oder CIDR, z. B. 192.168.1.50/24)" "$CT_IP"
[ "$CT_IP" = dhcp ] || ask CT_GATEWAY "Gateway" "$CT_GATEWAY"
if [ "$expert" = 1 ]; then
    ask CT_STORAGE "Storage für das Root-Dateisystem" "$CT_STORAGE"
    ask CT_TEMPLATE_STORAGE "Storage für Templates" "$CT_TEMPLATE_STORAGE"
    ask CT_CORES "CPU-Kerne" "$CT_CORES"
    ask CT_MEMORY "RAM (MiB)" "$CT_MEMORY"
    ask CT_SWAP "Swap (MiB)" "$CT_SWAP"
    ask CT_DISK_GB "Plattengröße (GB)" "$CT_DISK_GB"
    ask CT_BRIDGE "Netzwerkbrücke" "$CT_BRIDGE"
    ask CT_VLAN "VLAN-Tag (leer = keiner)" "$CT_VLAN"
    ask CT_DNS "DNS-Server (leer = vom Host)" "$CT_DNS"
fi

step "Angaben für JF-Manager (werden im Container nicht erneut abgefragt)"
: "${JF_ACTION:=install}" "${JF_VERSION:=}" "${JF_DOMAIN:=}" "${JF_TLS:=caddy}" "${JF_ACME_EMAIL:=}"
: "${JF_TIMEZONE:=Europe/Berlin}" "${JF_ADMIN_USER:=admin}" "${JF_ADMIN_EMAIL:=}"
: "${JF_BACKUP_REPO:=/var/backups/jf-manager/restic}" "${JF_BACKUP_PASSWORD:=}" "${JF_ADMIN_PASSWORD:=}"
: "${JF_HTTP_BIND:=0.0.0.0:8080}" "${JF_TRUSTED_PROXY_ADDRS:=}" "${JF_INSTANCE:=$CT_HOSTNAME}"
ask JF_VERSION "Releaseversion (X.Y.Z)" "$JF_VERSION"
valid_version "$JF_VERSION" || die "$EX_USAGE" "Ungültige Version '$JF_VERSION'."
JF_VERSION=${JF_VERSION#v}
ask JF_DOMAIN "Domain" "$JF_DOMAIN"
ask JF_TLS "HTTPS: caddy (integriert) oder proxy (vorhandener Reverse Proxy)" "$JF_TLS"
if [ "$JF_TLS" = caddy ]; then ask JF_ACME_EMAIL "Kontaktadresse für Zertifikate" "$JF_ACME_EMAIL"
else
    ask JF_HTTP_BIND "Adresse:Port für Nginx im Container" "$JF_HTTP_BIND"
    ask JF_TRUSTED_PROXY_ADDRS "IP-Adresse(n) des Reverse Proxy" "$JF_TRUSTED_PROXY_ADDRS"
fi
ask JF_BACKUP_REPO "Backup-Ziel im Container (besser sftp:/s3: oder ein eingebundener Pfad)" "$JF_BACKUP_REPO"
ask_secret JF_BACKUP_PASSWORD "Backup-Passwort"
if [ "$JF_ACTION" = install ]; then
    ask JF_ADMIN_USER "Erster Administrator" "$JF_ADMIN_USER"
    ask JF_ADMIN_EMAIL "E-Mail des Administrators" "$JF_ADMIN_EMAIL"
    ask_secret JF_ADMIN_PASSWORD "Administratorpasswort"
fi
register_secret "$JF_BACKUP_PASSWORD"; register_secret "$JF_ADMIN_PASSWORD"

# --- Preflight (nothing changed yet) ------------------------------------------------
step "Vorabprüfung"
failed=0
[[ $CT_ID =~ ^[0-9]+$ ]] && [ "$CT_ID" -ge 100 ] || { err "CT-ID muss eine Zahl ≥ 100 sein"; failed=1; }
if pct status "$CT_ID" >/dev/null 2>&1 || qm status "$CT_ID" >/dev/null 2>&1; then err "ID $CT_ID ist bereits vergeben"; failed=1; else ok "CT-ID $CT_ID frei"; fi
[[ $CT_HOSTNAME =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]] || { err "Ungültiger Hostname"; failed=1; }
if pvesm status -content rootdir 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$CT_STORAGE"; then
    avail=$(pvesm status -storage "$CT_STORAGE" 2>/dev/null | awk 'NR==2 {print $6}')
    if [ -n "$avail" ] && [ "$avail" -lt $(( (CT_DISK_GB + 2) * 1024 * 1024 )) ]; then err "Storage $CT_STORAGE hat zu wenig Platz"; failed=1
    else ok "Storage $CT_STORAGE"; fi
else err "Storage $CT_STORAGE fehlt oder erlaubt keine Container"; failed=1; fi
pvesm status -content vztmpl 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$CT_TEMPLATE_STORAGE" ||
    { err "Template-Storage $CT_TEMPLATE_STORAGE fehlt oder erlaubt keine Templates"; failed=1; }
ip link show "$CT_BRIDGE" >/dev/null 2>&1 && ok "Brücke $CT_BRIDGE" || { err "Netzwerkbrücke $CT_BRIDGE fehlt"; failed=1; }
if [ "$CT_IP" != dhcp ]; then
    [[ $CT_IP =~ ^[0-9.]+/[0-9]{1,2}$ ]] || { err "IP im CIDR-Format angeben"; failed=1; }
    [[ $CT_GATEWAY =~ ^[0-9.]+$ ]] || { err "Gateway fehlt"; failed=1; }
fi
[ "$CT_MEMORY" -ge 2048 ] || { err "Mindestens 2048 MiB RAM"; failed=1; }
[ "$CT_DISK_GB" -ge 8 ] || { err "Mindestens 8 GB Platte"; failed=1; }
[ -n "$JF_DOMAIN" ] || { err "Domain fehlt"; failed=1; }
case $JF_TLS in caddy) [ -n "$JF_ACME_EMAIL" ] || { err "Kontaktadresse für Zertifikate fehlt"; failed=1; } ;;
    proxy) [ -n "$JF_TRUSTED_PROXY_ADDRS" ] || { err "Adresse des Reverse Proxy fehlt"; failed=1; } ;;
    *) err "JF_TLS muss caddy oder proxy sein"; failed=1 ;; esac
if [ -n "$JF_BACKUP_PASSWORD" ] && [ ${#JF_BACKUP_PASSWORD} -lt 12 ]; then err "Backup-Passwort zu kurz (mindestens 12 Zeichen)"; failed=1; fi

# Release on the host: verified before it is pushed into the container.
work=$(mktemp -d /var/tmp/jf-lxc.XXXXXX)
trap 'rm -rf "$work"' EXIT
name="jf-manager-$JF_VERSION.tar.gz"
if [ -n "$release_dir" ]; then
    cp "$release_dir/$name" "$release_dir/release-manifest.json" "$release_dir/SHA256SUMS" "$work/" 2>/dev/null ||
        { err "Releasedateien fehlen in $release_dir"; failed=1; }
else
    base="${JF_RELEASE_URL:-https://github.com/Jugendfeuerwehr-Manager/JF-Manager/releases/download}/v$JF_VERSION"
    for f in SHA256SUMS release-manifest.json "$name"; do
        curl -fsSL --proto '=https' -o "$work/$f" "$base/$f" || { err "Download $f fehlgeschlagen"; failed=1; break; }
    done
fi
if [ "$failed" = 0 ]; then
    (cd "$work" && sha256sum --quiet --strict -c SHA256SUMS) && ok "Release $JF_VERSION geprüft (Prüfsummen)" ||
        { err "Prüfsummen stimmen nicht"; failed=1; }
fi

pveam update >/dev/null 2>&1 || warn "Templateliste nicht aktualisiert"
template=$(pveam list "$CT_TEMPLATE_STORAGE" 2>/dev/null | awk '{print $1}' | grep -E 'debian-13-standard_.*amd64' | sort -V | tail -1 || true)
if [ -z "$template" ]; then
    template_name=$(pveam available --section system 2>/dev/null | awk '{print $2}' | grep -E '^debian-13-standard_.*amd64' | sort -V | tail -1 || true)
    [ -n "$template_name" ] || { err "Kein Debian-13-Template verfügbar (pveam available)"; failed=1; }
fi
[ "$failed" = 0 ] || die "$EX_PRECHECK" "Vorabprüfung fehlgeschlagen – nichts wurde verändert."

net0="name=eth0,bridge=$CT_BRIDGE,ip=$CT_IP${CT_GATEWAY:+,gw=$CT_GATEWAY}${CT_VLAN:+,tag=$CT_VLAN},firewall=1"
cat <<EOF

Zusammenfassung
  Container:  $CT_ID ($CT_HOSTNAME), unprivilegiert, Debian 13, nesting=1, Autostart
  Ressourcen: $CT_CORES Kerne, $CT_MEMORY MiB RAM, $CT_SWAP MiB Swap, $CT_DISK_GB GB auf $CT_STORAGE
  Netzwerk:   $net0${CT_DNS:+, DNS $CT_DNS}
  Template:   ${template:-$template_name (wird geladen)}
  JF-Manager: $JF_VERSION, $JF_DOMAIN, $([ "$JF_TLS" = caddy ] && echo "integriertes HTTPS" || echo "Reverse Proxy $JF_TRUSTED_PROXY_ADDRS")
  Backup:     $JF_BACKUP_REPO
  Auf dem Host wird außer Template und Container nichts installiert.

EOF
confirm_yes "Container anlegen und JF-Manager darin installieren?" || die "$EX_ABORTED" "Abgebrochen – nichts verändert."

# --- Changes ----------------------------------------------------------------------------
if [ -z "$template" ]; then
    step "Template $template_name laden"
    (umask 022; pveam download "$CT_TEMPLATE_STORAGE" "$template_name") >/dev/null
    template="$CT_TEMPLATE_STORAGE:vztmpl/$template_name"
fi

step "Container $CT_ID anlegen"
create_args=(--hostname "$CT_HOSTNAME" --ostype debian --unprivileged 1 --features nesting=1
    --cores "$CT_CORES" --memory "$CT_MEMORY" --swap "$CT_SWAP"
    --rootfs "$CT_STORAGE:$CT_DISK_GB" --net0 "$net0" --onboot 1
    --description "JF-Manager $JF_VERSION (jfctl, nativer Betrieb)")
[ -n "$CT_DNS" ] && create_args+=(--nameserver "$CT_DNS")
# Proxmox unpacks the template as the mapped container root (uid 100000): with the
# restrictive umask of this script the new rootfs would not be writable for it.
(umask 022; pct create "$CT_ID" "$template" "${create_args[@]}") >/dev/null
pct start "$CT_ID"
ok "Container gestartet"

step "Warten auf Netzwerk im Container"
for _ in $(seq 1 60); do
    pct exec "$CT_ID" -- getent hosts deb.debian.org >/dev/null 2>&1 && break
    sleep 2
done
pct exec "$CT_ID" -- getent hosts deb.debian.org >/dev/null 2>&1 || die "$EX_ERROR" "Container hat kein Netzwerk (Container $CT_ID bleibt zur Analyse bestehen)."

step "Werkzeuge für jfctl im Container"
pct exec "$CT_ID" -- bash -c 'DEBIAN_FRONTEND=noninteractive apt-get update -q && DEBIAN_FRONTEND=noninteractive apt-get install -y -q jq curl openssl ca-certificates' >/dev/null

step "Release und Antworten übertragen"
pct exec "$CT_ID" -- mkdir -p /root/jf-release
for f in "$work"/*; do pct push "$CT_ID" "$f" "/root/jf-release/$(basename "$f")" --perms 0600; done
ans="$work/answers.env"
install -m 600 /dev/null "$ans"
for key in "${JF_PASS_KEYS[@]}"; do
    [ -n "${!key:-}" ] && kv_set "$ans" "$key" "${!key}"
done
kv_set "$ans" JF_MODE native
kv_set "$ans" JF_INSTANCE "$JF_INSTANCE"
kv_set "$ans" JF_RELEASE_DIR /root/jf-release
pct push "$CT_ID" "$ans" /root/jf-answers.env --perms 0600
rm -f "$ans"
pct exec "$CT_ID" -- tar -xzf "/root/jf-release/$name" -C /root/jf-release

step "Nativer Installationskern im Container"
rc=0
pct exec "$CT_ID" -- "/root/jf-release/jf-manager-$JF_VERSION/ops/jfctl" install --answers /root/jf-answers.env --yes || rc=$?
pct exec "$CT_ID" -- rm -f /root/jf-answers.env
if [ "$rc" -ne 0 ]; then
    die "$rc" "Installation im Container fehlgeschlagen (Code $rc). Fortsetzen: pct enter $CT_ID; jfctl install (setzt fort)."
fi
ip=$(pct exec "$CT_ID" -- hostname -I 2>/dev/null | awk '{print $1}')
cat <<EOF

JF-Manager läuft in Container $CT_ID ($CT_HOSTNAME, ${ip:-IP unbekannt}).
  Verwaltung:   pct enter $CT_ID   und dort   jfctl
  DNS:          $JF_DOMAIN → ${ip:-<IP des Containers>}$([ "$JF_TLS" = proxy ] && echo " (über den Reverse Proxy)")
  Backup-Passwort im Container: /etc/jf-manager/backup.pass – zusätzlich außerhalb aufbewahren.
EOF
