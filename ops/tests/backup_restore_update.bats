#!/usr/bin/env bats
# Failure paths of backup, restore and update with stubbed docker/restic.
# The full flows run against real containers in the acceptance (OPS-01.9).

load helpers

setup() {
    jf_minimal_install compose
    mkdir -p "$JFCTL_OPT/current/ops/compose"
    : >"$BATS_TEST_TMPDIR/calls"
    # docker: services report healthy; pg_dump fails when DUMP_FAILS is set
    jf_stub docker '
echo "docker $*" >>"$BATS_TEST_TMPDIR/calls"
case "$*" in
  *"pg_dump"*) [ -n "${DUMP_FAILS:-}" ] && exit 1; echo dumpdata ;;
  *"SHOW server_version_num"*) echo 170004 ;;
esac
exit 0'
    jf_stub restic '
echo "restic $*" >>"$BATS_TEST_TMPDIR/calls"
case "$1" in
  cat) # REPO_STATE: missing (exit 10 until init), password (12), unreachable (1)
    case "${REPO_STATE:-ok}" in
      ok) exit 0 ;;
      missing) [ -f "$BATS_TEST_TMPDIR/repo-created" ] && exit 0; exit 10 ;;
      password) exit 12 ;;
      *) exit 1 ;;
    esac ;;
  init) touch "$BATS_TEST_TMPDIR/repo-created" ;;
  backup) printf "%s\n" "{\"message_type\":\"summary\",\"snapshot_id\":\"abcdef1234567890\",\"total_files_processed\":4}" ;;
  restore) exit 1 ;;
esac
exit 0'
}

# Install of 1.0.0 behind the current link, a verifiable release 1.1.0 in $rel
# and docker reporting running workers, so an update can complete.
_update_fixture() {
    rm -rf "$JFCTL_OPT/current"
    mkdir -p "$JFCTL_OPT/releases/1.0.0/ops/compose"
    echo '{"version":"1.0.0"}' >"$JFCTL_OPT/releases/1.0.0/MANIFEST.json"
    ln -s releases/1.0.0 "$JFCTL_OPT/current"
    rel="$BATS_TEST_TMPDIR/rel"; pkg="$BATS_TEST_TMPDIR/pkg/jf-manager-1.1.0"
    mkdir -p "$rel" "$pkg"
    echo '{"version":"1.1.0"}' >"$pkg/MANIFEST.json"
    tar -czf "$rel/jf-manager-1.1.0.tar.gz" -C "$BATS_TEST_TMPDIR/pkg" jf-manager-1.1.0
    jq -n --arg sha "$(sha256sum "$rel/jf-manager-1.1.0.tar.gz" | awk '{print $1}')" \
        '{version:"1.1.0", tarball:{sha256:$sha}, images:{backend:"b@sha256:1", frontend:"f@sha256:2"}}' \
        >"$rel/release-manifest.json"
    (cd "$rel" && sha256sum jf-manager-1.1.0.tar.gz release-manifest.json >SHA256SUMS)
    export JF_VERIFY_ATTESTATION=off
    jf_stub docker '
echo "docker $*" >>"$BATS_TEST_TMPDIR/calls"
case "$*" in
  *"pg_dump"*) echo dumpdata ;;
  *"SHOW server_version_num"*) echo 170004 ;;
  *"ps --format"*) echo running ;;
esac
exit 0'
}

@test "failed database dump never reports a successful backup" {
    export DUMP_FAILS=1
    run "$OPS_DIR/jfctl" backup create
    [ "$status" -eq 1 ]
    [ "$(jq -r .status "$BATS_TEST_TMPDIR/data/state/last-backup.json")" = failed ]
    ! grep -q "^restic backup" "$BATS_TEST_TMPDIR/calls"
}

@test "successful backup records the snapshot and keeps the last success" {
    run "$OPS_DIR/jfctl" backup create
    [ "$status" -eq 0 ]
    [ "$(jq -r .status "$BATS_TEST_TMPDIR/data/state/last-backup.json")" = ok ]
    [ "$(jq -r .snapshot "$BATS_TEST_TMPDIR/data/state/last-backup.json")" = abcdef12 ]
    grep -q "restic backup .*--tag kind=manual" "$BATS_TEST_TMPDIR/calls"
    grep -q "restic forget .*--keep-daily 7 --keep-weekly 4 --keep-monthly 6" "$BATS_TEST_TMPDIR/calls"
    export DUMP_FAILS=1
    run "$OPS_DIR/jfctl" backup create
    [ "$(jq -r .last_success.snapshot "$BATS_TEST_TMPDIR/data/state/last-backup.json")" = abcdef12 ]
}

@test "backup publishes a readable status copy for the web view without secrets" {
    run "$OPS_DIR/jfctl" backup create
    [ "$status" -eq 0 ]
    public="$BATS_TEST_TMPDIR/data/ops-public/ops-status.json"
    [ "$(jq -r .last_backup.status "$public")" = ok ]
    [ "$(jq -r .instance "$public")" = test-instanz ]
    [ "$(stat -c %a "$public" 2>/dev/null || stat -f %Lp "$public")" = 644 ]
    [ "$(stat -c %a "$(dirname "$public")" 2>/dev/null || stat -f %Lp "$(dirname "$public")")" = 755 ]
    ! grep -Eq "secret-value|backup-pass" "$public"
}

@test "holding and releasing workers is visible in the published status" {
    public="$BATS_TEST_TMPDIR/data/ops-public/ops-status.json"
    run "$OPS_DIR/jfctl" workers hold
    [ "$status" -eq 0 ]
    [ "$(jq -r .workers_held "$public")" = true ]
    run "$OPS_DIR/jfctl" workers release
    [ "$status" -eq 0 ]
    [ "$(jq -r .workers_held "$public")" = false ]
}

@test "unreachable repository or wrong password stops before the maintenance window" {
    mkdir -p "$BATS_TEST_TMPDIR/repo"; : >"$BATS_TEST_TMPDIR/repo/config"
    export REPO_STATE=unreachable
    run "$OPS_DIR/jfctl" backup create
    [ "$status" -eq 3 ]
    [[ $output == *"nicht erreichbar"* ]]
    export REPO_STATE=password
    run "$OPS_DIR/jfctl" backup create
    [ "$status" -eq 3 ]
    [[ $output == *"Passwort für Backup-Repository"*"backup.pass"* ]]
    ! grep -q "stop frontend" "$BATS_TEST_TMPDIR/calls"
    ! grep -q "^restic init" "$BATS_TEST_TMPDIR/calls"
}

@test "old restic without exit code 10: local path without config counts as missing" {
    jf_stub restic 'exit 1'
    jf_source_libs; . "$OPS_DIR/lib/backup.sh"
    conf_load
    [ "$(backup_repo_state)" = missing ]
    mkdir -p "$JF_BACKUP_REPO"; : >"$JF_BACKUP_REPO/config"
    [ "$(backup_repo_state)" = unreachable ]
}

@test "missing repository is created when no backup ever succeeded (#25)" {
    export REPO_STATE=missing
    run "$OPS_DIR/jfctl" backup create
    [ "$status" -eq 0 ]
    [[ $output == *"fehlt und wird angelegt"* ]]
    [ "$(jq -r .status "$BATS_TEST_TMPDIR/data/state/last-backup.json")" = ok ]
    # created before the window, then backed up
    [ "$(grep -n "^restic init" "$BATS_TEST_TMPDIR/calls" | cut -d: -f1)" -lt "$(grep -n "stop frontend" "$BATS_TEST_TMPDIR/calls" | cut -d: -f1)" ]
    grep -q "^restic backup" "$BATS_TEST_TMPDIR/calls"
}

@test "missing repository after successful backups is not recreated silently" {
    run "$OPS_DIR/jfctl" backup create
    [ "$status" -eq 0 ]
    : >"$BATS_TEST_TMPDIR/calls"
    export REPO_STATE=missing
    run "$OPS_DIR/jfctl" backup create
    [ "$status" -eq 3 ]
    [[ $output == *"zuletzt gesichert"*"jfctl backup init"* ]]
    ! grep -q "^restic init" "$BATS_TEST_TMPDIR/calls"
    ! grep -q "stop frontend" "$BATS_TEST_TMPDIR/calls"
    run "$OPS_DIR/jfctl" backup init
    [ "$status" -eq 0 ]
    grep -q "^restic init" "$BATS_TEST_TMPDIR/calls"
}

@test "update checks the repository before the maintenance window" {
    run "$OPS_DIR/jfctl" backup create
    : >"$BATS_TEST_TMPDIR/calls"
    export REPO_STATE=missing
    _update_fixture
    run "$OPS_DIR/jfctl" --yes update --version 1.1.0 --release-dir "$rel"
    [ "$status" -eq 3 ]
    [[ $output == *"jfctl backup init"* ]]
    ! grep -q " stop " "$BATS_TEST_TMPDIR/calls"
    [ ! -f "$BATS_TEST_TMPDIR/data/state/update.state" ]
}

@test "restore of an unreadable snapshot changes nothing" {
    run "$OPS_DIR/jfctl" --non-interactive restore abcdef12 --confirm test-instanz
    [ "$status" -eq 3 ]
    ! grep -Eq "ALTER DATABASE|stop |DROP DATABASE" "$BATS_TEST_TMPDIR/calls"
}

@test "restore requires an id" {
    run "$OPS_DIR/jfctl" restore
    [ "$status" -eq 2 ]
}

@test "update refuses invalid, older and equal versions without changes" {
    run "$OPS_DIR/jfctl" --yes update --version main
    [ "$status" -eq 2 ]
    run "$OPS_DIR/jfctl" --yes update --version 0.9.0
    [ "$status" -eq 3 ]
    run "$OPS_DIR/jfctl" --yes update --version 1.0.0
    [ "$status" -eq 0 ]
    [[ $output == *"bereits installiert"* ]]
    ! grep -q "stop" "$BATS_TEST_TMPDIR/calls"
}

@test "update refuses a release with mismatching checksums" {
    rel="$BATS_TEST_TMPDIR/rel"; mkdir -p "$rel"
    echo payload >"$rel/jf-manager-1.1.0.tar.gz"
    echo '{"version":"1.1.0","tarball":{"sha256":"x"}}' >"$rel/release-manifest.json"
    (cd "$rel" && sha256sum jf-manager-1.1.0.tar.gz release-manifest.json >SHA256SUMS)
    echo tampered >>"$rel/jf-manager-1.1.0.tar.gz"
    export JF_VERIFY_ATTESTATION=off
    run "$OPS_DIR/jfctl" --yes update --version 1.1.0 --release-dir "$rel"
    [ "$status" -eq 3 ]
    [[ $output == *Prüfsummen* ]]
}

@test "an unfinished update blocks the next one" {
    printf 'STAGE=migrate\n' >"$BATS_TEST_TMPDIR/data/state/update.state"
    run "$OPS_DIR/jfctl" --yes update --version 1.1.0
    [ "$status" -eq 3 ]
    [[ $output == *unvollständig* ]]
}

@test "update without CSP_REPORT_ONLY in app.env switches to the new release" {
    # app.env from jf_minimal_install has no CSP_REPORT_ONLY, like real installs (#25).
    _update_fixture
    run "$OPS_DIR/jfctl" --yes update --version 1.1.0 --release-dir "$rel"
    [ "$status" -eq 0 ]
    [[ $output != *fehlgeschlagen* ]]
    [[ $output == *"Update auf 1.1.0 abgeschlossen"* ]]
    [ "$(readlink "$JFCTL_OPT/current")" = releases/1.1.0 ]
    grep -qx 'JF_VERSION=1.1.0' "$JFCTL_ETC/jfctl.conf"
    grep -qx 'JF_VERSION=1.1.0' "$JFCTL_ETC/compose.env"
    grep -qx 'default enforce;' "$JFCTL_ETC/csp-mode.conf"
}

@test "update corrects a recorded version that never started (#25)" {
    _update_fixture
    sed -i 's/^JF_VERSION=.*/JF_VERSION=1.1.0/' "$JFCTL_ETC/jfctl.conf"
    run "$OPS_DIR/jfctl" doctor
    [[ $output == *"nennt Version 1.1.0, es läuft 1.0.0"* ]]
    run "$OPS_DIR/jfctl" --yes update --version 1.1.0 --release-dir "$rel"
    [ "$status" -eq 0 ]
    [[ $output == *"es läuft aber 1.0.0"* ]]
    [[ $output == *"Wechsel 1.0.0 → 1.1.0"* ]]
    [ "$(readlink "$JFCTL_OPT/current")" = releases/1.1.0 ]
    grep -qx 'JF_VERSION=1.1.0' "$JFCTL_ETC/compose.env"
}

@test "answer files readable by others are refused" {
    rm -f "$JFCTL_ETC/jfctl.conf"
    printf 'JF_ACTION=install\n' >"$BATS_TEST_TMPDIR/answers.env"
    chmod 644 "$BATS_TEST_TMPDIR/answers.env"
    run "$OPS_DIR/jfctl" install --answers "$BATS_TEST_TMPDIR/answers.env"
    [ "$status" -eq 3 ]
    chmod 600 "$BATS_TEST_TMPDIR/answers.env"
    printf 'JF_UNKNOWN=1\n' >>"$BATS_TEST_TMPDIR/answers.env"
    run "$OPS_DIR/jfctl" install --answers "$BATS_TEST_TMPDIR/answers.env"
    [ "$status" -eq 2 ]
}

@test "install refuses to run over an existing installation" {
    run "$OPS_DIR/jfctl" install
    [ "$status" -eq 3 ]
    [[ $output == *"bereits installiert"* ]]
}
