# Shared setup for jfctl bats tests: isolated paths, no root, no real services.
OPS_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"

jf_test_env() {
    export JFCTL_ETC="$BATS_TEST_TMPDIR/etc"
    export JFCTL_OPT="$BATS_TEST_TMPDIR/opt"
    export JFCTL_LOG_DIR="$BATS_TEST_TMPDIR/log"
    export JFCTL_LOCK_FILE="$BATS_TEST_TMPDIR/jfctl.lock"
    export JFCTL_ALLOW_NONROOT=1
    export JFCTL_NO_SBIN_LINK=1
    export JF_NONINTERACTIVE=1
    mkdir -p "$JFCTL_ETC" "$JFCTL_OPT" "$JFCTL_LOG_DIR"
}

jf_source_libs() {
    jf_test_env
    # shellcheck source=../lib/common.sh
    . "$OPS_DIR/lib/common.sh"
    # shellcheck source=../lib/release.sh
    . "$OPS_DIR/lib/release.sh"
}

# Puts fake commands (docker, systemctl, restic …) first in PATH.
jf_stub() { # name body
    mkdir -p "$BATS_TEST_TMPDIR/bin"
    printf '#!/usr/bin/env bash\n%s\n' "$2" >"$BATS_TEST_TMPDIR/bin/$1"
    chmod +x "$BATS_TEST_TMPDIR/bin/$1"
    export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
}

jf_minimal_install() { # mode
    jf_test_env
    cat >"$JFCTL_ETC/jfctl.conf" <<CONF
JF_MODE=$1
JF_VERSION=1.0.0
JF_INSTANCE=test-instanz
JF_DOMAIN=jf.example.org
JF_TLS=caddy
JF_ACME_EMAIL=admin@example.org
JF_DATA_DIR=$BATS_TEST_TMPDIR/data
JF_BACKUP_REPO=$BATS_TEST_TMPDIR/repo
JF_BACKUP_PASSWORD_FILE=$JFCTL_ETC/backup.pass
CONF
    printf 'POSTGRES_PASSWORD=pg-secret-value\n' >"$JFCTL_ETC/secrets.env"
    printf "DJANGO_SECRET_KEY=django-secret-value\nFIELD_ENCRYPTION_KEY=fernet-secret-value\nALLOWED_HOSTS=jf.example.org\nCSRF_TRUSTED_ORIGINS=https://jf.example.org\nFRONTEND_URL=https://jf.example.org\n" >"$JFCTL_ETC/app.env"
    printf 'backup-pass\n' >"$JFCTL_ETC/backup.pass"
    chmod 600 "$JFCTL_ETC"/*
    mkdir -p "$BATS_TEST_TMPDIR/data/state"
}
