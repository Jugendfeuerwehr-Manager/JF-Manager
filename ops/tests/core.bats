#!/usr/bin/env bats
# Core behaviour of jfctl: configuration files, redaction, locking, exit codes.

load helpers

setup() { jf_source_libs; }

@test "kv_set/kv_get keep values with shell metacharacters literally" {
    f="$BATS_TEST_TMPDIR/app.env"
    kv_set "$f" EMAIL_HOST_PASSWORD 'p$a`ss w"rd;$(id)'
    kv_set "$f" ALLOWED_HOSTS 'a.example.org,b.example.org'
    run kv_get "$f" EMAIL_HOST_PASSWORD
    [ "$status" -eq 0 ]
    [ "$output" = 'p$a`ss w"rd;$(id)' ]
    [ "$(kv_get "$f" ALLOWED_HOSTS)" = 'a.example.org,b.example.org' ]
    [ "$(stat -c %a "$f")" = 600 ]
    grep -qx "EMAIL_HOST_PASSWORD='p\$a\`ss w\"rd;\$(id)'" "$f"
}

@test "kv_set replaces existing keys and keeps other lines" {
    f="$BATS_TEST_TMPDIR/x.env"
    printf '# comment\nA=1\nB=2\n' >"$f"
    kv_set "$f" A 3
    [ "$(cat "$f")" = $'# comment\nA=3\nB=2' ]
}

@test "kv_set refuses single quotes and newlines" {
    f="$BATS_TEST_TMPDIR/x.env"
    run kv_set "$f" A "it's"
    [ "$status" -eq "$EX_USAGE" ]
    run kv_set "$f" A $'a\nb'
    [ "$status" -eq "$EX_USAGE" ]
}

@test "kv_validate rejects unquoted values with spaces or metacharacters" {
    f="$BATS_TEST_TMPDIR/x.env"
    printf 'A=ok\nB=two words\n' >"$f"
    run kv_validate "$f"
    [ "$status" -ne 0 ]
    printf "A=ok\nB='two words'\n" >"$f"
    run kv_validate "$f"
    [ "$status" -eq 0 ]
}

@test "redact hides registered secrets, URL credentials and KEY assignments" {
    register_secret "topsecretvalue"
    run redact "x topsecretvalue y postgres://user:pw123@db/x DJANGO_SECRET_KEY=abc"
    [[ $output != *topsecretvalue* ]]
    [[ $output != *pw123* ]]
    [[ $output != *=abc* ]]
}

@test "version_cmp orders semantic versions" {
    [ "$(version_cmp 1.2.0 1.10.0)" = -1 ]
    [ "$(version_cmp v2.0.0 1.9.9)" = 1 ]
    [ "$(version_cmp 1.0.0 1.0.0)" = 0 ]
    valid_version 1.4.0
    ! valid_version 1.4
    ! valid_version 'main'
}

@test "second mutating command fails with EX_LOCKED" {
    ( acquire_lock first; sleep 3 ) &
    sleep 1
    run bash -c ". '$OPS_DIR/lib/common.sh'; acquire_lock second"
    [ "$status" -eq 4 ]
    [[ $output == *"first"* ]]
    wait
}

@test "trusted proxy list contains only configured proxies in proxy mode" {
    JF_TLS=proxy JF_TRUSTED_PROXY_ADDRS="192.168.1.10 10.0.0.0/24"
    render_trusted_proxies native
    run grep -v '^#' "$JF_TRUSTED_PROXIES"
    [ "$output" = $'192.168.1.10 1;\n10.0.0.0/24 1;' ]
    JF_TRUSTED_PROXY_ADDRS="1.2.3.4;rm"
    run render_trusted_proxies native
    [ "$status" -eq "$EX_USAGE" ]
}

@test "CSP mode follows CSP_REPORT_ONLY and enforces by default" {
    render_csp_mode
    [ "$(grep -v '^#' "$JF_CSP_MODE")" = "default enforce;" ]
    kv_set "$JF_APP_ENV" CSP_REPORT_ONLY True
    render_csp_mode
    [ "$(grep -v '^#' "$JF_CSP_MODE")" = "default report-only;" ]
    kv_set "$JF_APP_ENV" CSP_REPORT_ONLY false
    render_csp_mode
    [ "$(grep -v '^#' "$JF_CSP_MODE")" = "default enforce;" ]
}

@test "jfctl: unknown command exits 2, missing installation exits 8" {
    run "$OPS_DIR/jfctl" frobnicate
    [ "$status" -eq 2 ]
    run "$OPS_DIR/jfctl" status
    [ "$status" -eq 8 ]
}

@test "jfctl help lists all documented commands" {
    run "$OPS_DIR/jfctl" --help
    [ "$status" -eq 0 ]
    for c in install status doctor start stop restart logs update backup restore config admin workers maintenance migrate; do
        grep -Eq "^  ($c |.*\| $c( |$))" <<<"$output" || { echo "missing $c"; return 1; }
    done
}

@test "config set validates and refuses unknown keys" {
    jf_minimal_install compose
    jf_stub docker 'exit 0'
    run "$OPS_DIR/jfctl" config set JF_TLS bogus
    [ "$status" -eq "$EX_USAGE" ]
    run "$OPS_DIR/jfctl" config set DJANGO_SECRET_KEY x
    [ "$status" -eq "$EX_USAGE" ]
    [ "$(kv_get "$JFCTL_ETC/app.env" DJANGO_SECRET_KEY)" = django-secret-value ]
}

@test "config show masks secrets" {
    jf_minimal_install compose
    run "$OPS_DIR/jfctl" config show
    [ "$status" -eq 0 ]
    [[ $output != *django-secret-value* ]]
    [[ $output != *fernet-secret-value* ]]
    [[ $output == *"ALLOWED_HOSTS"*"jf.example.org"* ]]
}

@test "log file never contains registered secrets" {
    jf_minimal_install compose
    jf_stub docker 'echo "DATABASE_URL=postgres://jf_manager:pg-secret-value@db/jf"; exit 0'
    run "$OPS_DIR/jfctl" logs backend
    ! grep -rq "pg-secret-value" "$JFCTL_LOG_DIR"
    [[ $output != *pg-secret-value* ]]
}

@test "admin reset-mfa runs the management command after confirmation" {
    jf_minimal_install compose
    : >"$BATS_TEST_TMPDIR/calls"
    jf_stub docker 'echo "docker $*" >>"$BATS_TEST_TMPDIR/calls"'
    run "$OPS_DIR/jfctl" --non-interactive admin reset-mfa --user chef
    [ "$status" -eq 5 ]
    ! grep -q reset_mfa "$BATS_TEST_TMPDIR/calls"
    run "$OPS_DIR/jfctl" --yes admin reset-mfa --user chef
    [ "$status" -eq 0 ]
    grep -q "run --rm --no-deps -T -e DJANGO_COLLECTSTATIC=off backend python manage.py reset_mfa --user chef" "$BATS_TEST_TMPDIR/calls"
}

@test "custom compose project is persisted and used by later commands" {
    jf_minimal_install compose
    conf_load
    JF_COMPOSE_PROJECT=jf-manager-v3
    conf_save
    unset JF_COMPOSE_PROJECT
    conf_load
    [ "$JF_COMPOSE_PROJECT" = jf-manager-v3 ]
    jf_stub docker 'printf "%s\n" "$*" >>"$BATS_TEST_TMPDIR/calls"'
    run "$OPS_DIR/jfctl" stop
    [ "$status" -eq 0 ]
    grep -q '^compose -p jf-manager-v3 ' "$BATS_TEST_TMPDIR/calls"
    ! grep -q '^compose -p jf-manager ' "$BATS_TEST_TMPDIR/calls"
}

@test "invalid compose project is refused before configuration is saved" {
    . "$OPS_DIR/lib/basic.sh"
    jf_minimal_install compose
    conf_load
    JF_COMPOSE_PROJECT='../old stack'
    run config_validate
    [ "$status" -eq 1 ]
    [[ $output == *"JF_COMPOSE_PROJECT"* ]]
}
