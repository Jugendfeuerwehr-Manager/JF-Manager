#!/usr/bin/env bats
load helpers

setup() {
    jf_source_libs
    . "$OPS_DIR/lib/departments.sh"
    export CALLS="$BATS_TEST_TMPDIR/calls"
    : >"$CALLS"
    JFCTL_HOME=$OPS_DIR
    JF_INSTANCE=test-instanz
    JF_DATA_DIR="$BATS_TEST_TMPDIR/data"
    mkdir -p "$JF_DATA_DIR"
    need_root() { :; }
    require_installed() { :; }
    load_adapter() { :; }
    acquire_lock() { :; }
    ad_entry_stop() { echo entry-stop >>"$CALLS"; }
    ad_app_stop() { echo app-stop >>"$CALLS"; }
    _backup_window_end() { echo restart >>"$CALLS"; }
    backup_in_window() { echo backup >>"$CALLS"; BACKUP_LAST_SNAPSHOT=abcdef12; [ "${BACKUP_FAIL:-0}" != 1 ]; }
    backup_fetch() { echo verify >>"$CALLS"; [ "${VERIFY_FAIL:-0}" != 1 ]; }
    backup_check_fetched() { :; }
    ad_health_internal() { :; }
    write_ops_status() { :; }
    ad_manage() {
        echo manage >>"$CALLS"
        if [[ $* == *apply=True* ]]; then
            echo apply >>"$CALLS"
            [ "${APPLY_FAIL:-0}" != 1 ] || return 1
        fi
        printf '{"conflicts":%s,"fingerprint":"%064d","counts":{}}\n' "${CONFLICTS:-[]}" 0
    }
}

@test "department preview makes no changes and requires explicit areas" {
    run cmd_departments move --from global --to jugendfeuerwehr --areas members
    [ "$status" = 0 ]
    ! grep -Eq 'stop|backup|apply' "$CALLS"
    run cmd_departments move --from global --to jugendfeuerwehr
    [ "$status" = 2 ]
}

@test "apply requires instance confirmation even with yes" {
    JF_ASSUME_YES=1
    run cmd_departments move --from global --to jugendfeuerwehr --areas members --apply
    [ "$status" = 2 ]
    ! grep -Eq 'stop|backup|apply' "$CALLS"
}

@test "conflicts refuse before stopping services" {
    CONFLICTS='["conflict"]'
    run cmd_departments move --from global --to jugendfeuerwehr --areas members --apply --confirm test-instanz
    [ "$status" = 3 ]
    ! grep -Eq 'stop|backup|apply' "$CALLS"
}

@test "apply stops writes then backs up and verifies before moving" {
    run cmd_departments move --from global --to jugendfeuerwehr --areas members --apply --confirm test-instanz
    [ "$status" = 0 ]
    [ "$(cat "$CALLS")" = $'manage\nentry-stop\napp-stop\nbackup\nverify\nmanage\napply\nrestart' ]
}

@test "failed backup reopens application and never applies" {
    BACKUP_FAIL=1
    run cmd_departments move --from global --to jugendfeuerwehr --areas members --apply --confirm test-instanz
    [ "$status" = 1 ]
    ! grep -q apply "$CALLS"
    grep -q restart "$CALLS"
}

@test "failed verification reopens application and never applies" {
    VERIFY_FAIL=1
    run cmd_departments move --from global --to jugendfeuerwehr --areas members --apply --confirm test-instanz
    [ "$status" = 6 ]
    ! grep -q apply "$CALLS"
    grep -q restart "$CALLS"
}

@test "rolled back transfer reopens application" {
    APPLY_FAIL=1
    run cmd_departments move --from global --to jugendfeuerwehr --areas members --apply --confirm test-instanz
    [ "$status" = 1 ]
    grep -q restart "$CALLS"
}

@test "missing option value is usage error" {
    run cmd_departments move --from
    [ "$status" = 2 ]
}

@test "originally stopped application stays stopped" {
    ad_health_internal() { return 1; }
    run cmd_departments move --from global --to jugendfeuerwehr --areas members --apply --confirm test-instanz
    [ "$status" = 0 ]
    grep -q apply "$CALLS"
    ! grep -q restart "$CALLS"
}
