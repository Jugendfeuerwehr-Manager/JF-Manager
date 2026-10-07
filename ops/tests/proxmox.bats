#!/usr/bin/env bats
# Proxmox host component with stubbed pct/pveam/pvesm. A real Proxmox VE run
# is still required for acceptance (roadmap 5.4 "Betrieb").

load helpers

setup() {
    jf_test_env
    export JFCTL_LOG_DIR="$BATS_TEST_TMPDIR/log"
    : >"$BATS_TEST_TMPDIR/calls"
    jf_stub pveversion 'echo "pve-manager/9.0.6/abcdef (running kernel: 6.14)"'
    jf_stub pvesh 'echo 123'
    jf_stub qm 'exit 1'
    jf_stub pvesm 'echo "pvesm $*" >>"$BATS_TEST_TMPDIR/calls"
case "$*" in
  *"-content rootdir"*) printf "Name Type Status Total Used Available %%\nlocal-lvm lvmthin active 100 1 99999999 1\n" ;;
  *"-content vztmpl"*) printf "Name Type Status Total Used Available %%\nlocal dir active 100 1 99999999 1\n" ;;
  *"-storage local-lvm"*) printf "Name Type Status Total Used Available %%\nlocal-lvm lvmthin active 100 1 99999999 1\n" ;;
esac'
    jf_stub pveam 'echo "pveam $*" >>"$BATS_TEST_TMPDIR/calls"
case "$1" in
  list) echo "local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst 123" ;;
esac'
    jf_stub pct 'echo "pct $*" >>"$BATS_TEST_TMPDIR/calls"
case "$1" in
  status) [ -n "${CT_TAKEN:-}" ] && exit 0; exit 2 ;;
  push) cp "$3" "$BATS_TEST_TMPDIR/pushed-$(basename "$4")"; stat -c %a "$3" >"$BATS_TEST_TMPDIR/pushed-$(basename "$4").mode" ;;
  exec) case "$*" in *"hostname -I"*) echo 192.168.1.50 ;; esac ;;
esac
exit 0'
    jf_stub ip 'exit 0'
    jf_stub dpkg 'echo amd64'
    jf_stub apt-get 'echo "HOST apt-get $*" >>"$BATS_TEST_TMPDIR/calls"'
    rel="$BATS_TEST_TMPDIR/rel"; mkdir -p "$rel"
    echo payload >"$rel/jf-manager-1.0.0.tar.gz"; echo '{}' >"$rel/release-manifest.json"
    (cd "$rel" && sha256sum jf-manager-1.0.0.tar.gz release-manifest.json >SHA256SUMS)
    ans="$BATS_TEST_TMPDIR/ct.env"
    cat >"$ans" <<ANS
CT_ID=123
CT_HOSTNAME=jf-test
JF_VERSION=1.0.0
JF_DOMAIN=jf.example.org
JF_TLS=caddy
JF_ACME_EMAIL=it@example.org
JF_BACKUP_PASSWORD='backup-passwort-lang'
JF_ADMIN_PASSWORD='admin-passwort-lang'
ANS
    chmod 600 "$ans"
}

@test "creates an unprivileged Debian 13 container and runs the native core inside" {
    run "$OPS_DIR/proxmox/jf-lxc.sh" --release-dir "$rel" --answers "$ans" --yes
    [ "$status" -eq 0 ]
    grep -q "pct create 123 local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst .*--unprivileged 1 --features nesting=1" "$BATS_TEST_TMPDIR/calls"
    grep -q "pct exec 123 -- /root/jf-release/jf-manager-1.0.0/ops/jfctl install --answers /root/jf-answers.env --yes" "$BATS_TEST_TMPDIR/calls"
    grep -q "pct exec 123 -- rm -f /root/jf-answers.env" "$BATS_TEST_TMPDIR/calls"
    grep -q "^JF_MODE=native" "$BATS_TEST_TMPDIR/pushed-jf-answers.env"
    [ "$(cat "$BATS_TEST_TMPDIR/pushed-jf-answers.env.mode")" = 600 ]
    ! grep -q "HOST apt-get" "$BATS_TEST_TMPDIR/calls"
}

@test "secrets never appear in pct arguments or the log" {
    run "$OPS_DIR/proxmox/jf-lxc.sh" --release-dir "$rel" --answers "$ans" --yes
    ! grep -q "backup-passwort-lang\|admin-passwort-lang" "$BATS_TEST_TMPDIR/calls"
    ! grep -rq "backup-passwort-lang\|admin-passwort-lang" "$BATS_TEST_TMPDIR/log"
}

@test "taken CT id fails the preflight without creating anything" {
    export CT_TAKEN=1
    run "$OPS_DIR/proxmox/jf-lxc.sh" --release-dir "$rel" --answers "$ans" --yes
    [ "$status" -eq 3 ]
    ! grep -q "pct create" "$BATS_TEST_TMPDIR/calls"
}

@test "tampered release fails the preflight" {
    echo x >>"$rel/jf-manager-1.0.0.tar.gz"
    run "$OPS_DIR/proxmox/jf-lxc.sh" --release-dir "$rel" --answers "$ans" --yes
    [ "$status" -eq 3 ]
    ! grep -q "pct create" "$BATS_TEST_TMPDIR/calls"
}

@test "refuses to run outside Proxmox" {
    rm "$BATS_TEST_TMPDIR/bin/pct"
    PATH="$BATS_TEST_TMPDIR/bin:/usr/bin:/bin" run "$OPS_DIR/proxmox/jf-lxc.sh" --answers "$ans" --yes
    [ "$status" -eq 3 ]
}
