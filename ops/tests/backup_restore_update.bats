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
  cat) [ -n "${REPO_BROKEN:-}" ] && exit 1; exit 0 ;;
  backup) printf "%s\n" "{\"message_type\":\"summary\",\"snapshot_id\":\"abcdef1234567890\",\"total_files_processed\":4}" ;;
  restore) exit 1 ;;
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

@test "unreachable repository or wrong password stops before the maintenance window" {
    export REPO_BROKEN=1
    run "$OPS_DIR/jfctl" backup create
    [ "$status" -eq 3 ]
    ! grep -q "stop frontend" "$BATS_TEST_TMPDIR/calls"
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
