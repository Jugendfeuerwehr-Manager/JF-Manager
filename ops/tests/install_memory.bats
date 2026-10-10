#!/usr/bin/env bats

load helpers

setup() {
    jf_source_libs
    . "$OPS_DIR/lib/install.sh"
}

@test "small host is refused by default" {
    run _install_check_memory $((1753 * 1024 * 1024))
    [ "$status" -eq 1 ]
    [[ $output == *"Mindestens 2 GB RAM"* ]]
}

@test "explicit memory override allows a small host and warns" {
    run _install_check_memory $((1753 * 1024 * 1024)) 1
    [ "$status" -eq 0 ]
    [[ $output == *"--ignore-memory-check übergangen"* ]]
}

@test "minimum usable memory passes without override" {
    run _install_check_memory $((1900 * 1024 * 1024))
    [ "$status" -eq 0 ]
    [[ $output == *"Arbeitsspeicher"* ]]
    [[ $output != *"übergangen"* ]]
}

@test "memory override does not bypass other preflight failures" {
    conf_defaults
    JF_DOMAIN=jf.example.org
    JF_TLS=proxy
    JF_DATA_DIR="$BATS_TEST_TMPDIR/data"
    JF_ACTION=import
    config_validate() { return 0; }
    ad_preflight() { err "Docker-Dienst nicht erreichbar"; return 1; }
    free_bytes() { echo 10737418240; }
    _port_in_use() { return 1; }
    awk() { echo $((1753 * 1024 * 1024)); }
    release_fetch() { touch "$BATS_TEST_TMPDIR/release-fetched"; }
    run install_preflight 1
    [ "$status" -eq 1 ]
    [[ $output == *"--ignore-memory-check übergangen"* ]]
    [[ $output == *"Docker-Dienst nicht erreichbar"* ]]
    [ ! -e "$BATS_TEST_TMPDIR/release-fetched" ]
}

@test "CLI accepts override but still refuses an existing installation" {
    jf_minimal_install compose
    run "$OPS_DIR/jfctl" install --ignore-memory-check
    [ "$status" -eq 3 ]
    [[ $output == *"bereits installiert"* ]]
}

@test "CLI override reaches preflight and preserves Docker failure" {
    jf_stub awk 'if [[ "$*" == *MemTotal* ]]; then echo 1838153728; else exec /usr/bin/awk "$@"; fi'
    jf_stub docker 'case "$*" in "compose version"*) echo "2.20.1" ;; info) exit 1 ;; esac'
    cat >"$BATS_TEST_TMPDIR/answers.env" <<EOF
JF_ACTION=install
JF_MODE=compose
JF_VERSION=3.0.2
JF_DOMAIN=jf.example.org
JF_TLS=proxy
JF_HTTP_BIND=127.0.0.1:8080
JF_TRUSTED_PROXY_ADDRS=127.0.0.1
JF_DATA_DIR=$BATS_TEST_TMPDIR/data
JF_BACKUP_REPO=$BATS_TEST_TMPDIR/repo
EOF
    chmod 600 "$BATS_TEST_TMPDIR/answers.env"
    run "$OPS_DIR/jfctl" install --answers "$BATS_TEST_TMPDIR/answers.env" --ignore-memory-check
    [ "$status" -eq 3 ]
    [[ $output == *"--ignore-memory-check übergangen"* ]]
    [[ $output == *"Docker-Dienst nicht erreichbar"* ]]
    [ ! -e "$JFCTL_ETC/install.state" ]
}
