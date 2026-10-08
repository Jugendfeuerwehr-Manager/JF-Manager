#!/usr/bin/env bats
# Maintenance schedule: timers, task execution through the adapter, skipping.

load helpers

setup() {
    jf_minimal_install compose
    export JFCTL_SYSTEMD_DIR="$BATS_TEST_TMPDIR/systemd" JFCTL_ASSUME_SYSTEMD=1 JFCTL_SBIN=/usr/local/sbin/jfctl
    mkdir -p "$JFCTL_SYSTEMD_DIR"
    jf_stub systemctl 'echo "systemctl $*" >>"$BATS_TEST_TMPDIR/calls"'
    jf_stub docker 'echo "docker $*" >>"$BATS_TEST_TMPDIR/calls"'
}

@test "list shows all tasks and the backup schedule" {
    run "$OPS_DIR/jfctl" maintenance list
    [ "$status" -eq 0 ]
    for t in sessions export-audits booking-requests sync-due portal-access inbox registration-notes order-reminders backup; do
        [[ $output == *"$t"* ]]
    done
    grep -q "order-reminders *nein" <<<"$output"
}

@test "run executes the management command through the adapter" {
    run "$OPS_DIR/jfctl" maintenance run sessions
    [ "$status" -eq 0 ]
    grep -q "docker compose -p jf-manager .* run --rm --no-deps -T -e DJANGO_COLLECTSTATIC=off backend python manage.py clearsessions" "$BATS_TEST_TMPDIR/calls"
}

@test "run of an unknown task is a usage error" {
    run "$OPS_DIR/jfctl" maintenance run nonsense
    [ "$status" -eq 2 ]
}

@test "run is skipped while another jfctl operation holds the lock" {
    ( exec 9>"$JFCTL_LOCK_FILE"; flock 9; sleep 3 ) &
    sleep 1
    run "$OPS_DIR/jfctl" maintenance run sessions
    [ "$status" -eq 0 ]
    [[ $output == *übersprungen* ]]
    [ ! -f "$BATS_TEST_TMPDIR/calls" ] || ! grep -q clearsessions "$BATS_TEST_TMPDIR/calls"
    wait
}

@test "sync-due is skipped while workers are held after a restore" {
    echo "restore" >"$BATS_TEST_TMPDIR/data/state/workers-held"
    run "$OPS_DIR/jfctl" maintenance run sync-due
    [ "$status" -eq 0 ]
    [[ $output == *"Worker angehalten"* ]]
}

@test "timers are written, valid and only default tasks enabled" {
    run "$OPS_DIR/jfctl" maintenance install-timers
    [ "$status" -eq 0 ]
    [ -f "$JFCTL_SYSTEMD_DIR/jf-manager-backup.timer" ]
    grep -q "OnCalendar=\*-\*-\* 02:30:00" "$JFCTL_SYSTEMD_DIR/jf-manager-backup.timer"
    grep -q "enable --now jf-manager-maint-sessions.timer" "$BATS_TEST_TMPDIR/calls"
    grep -q "disable --now jf-manager-maint-order-reminders.timer" "$BATS_TEST_TMPDIR/calls"
    for t in "$JFCTL_SYSTEMD_DIR"/*.timer; do
        grep -E '^OnCalendar=' "$t" | cut -d= -f2- | while read -r cal; do
            systemd-analyze calendar "$cal" >/dev/null
        done
    done
}

@test "enable switches an optional task on" {
    run "$OPS_DIR/jfctl" maintenance enable order-reminders
    [ "$status" -eq 0 ]
    grep -q "enable --now jf-manager-maint-order-reminders.timer" "$BATS_TEST_TMPDIR/calls"
    run "$OPS_DIR/jfctl" maintenance list
    grep -q "order-reminders *ja" <<<"$output"
}
