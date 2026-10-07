# shellcheck shell=bash
# Native Debian 13 adapter (also used inside the Proxmox LXC). Same interface
# as adapter-compose.sh. Services: PostgreSQL and Redis from Debian, uWSGI web,
# RQ worker, push worker and a dedicated nginx instance as systemd units,
# Caddy (Debian package) for integrated HTTPS.

JF_SERVICE_USER=${JF_SERVICE_USER:-jfmanager}
NATIVE_APP_UNITS=(jf-manager-web.service jf-manager-worker.service jf-manager-push.service)
NATIVE_WORKER_UNITS=(jf-manager-worker.service jf-manager-push.service)
NATIVE_ENTRY_UNITS=(jf-manager-nginx.service)
NATIVE_PACKAGES=(python3 python3-venv python3-dev build-essential pkg-config libpq-dev
    libldap2-dev libsasl2-dev libssl-dev default-libmysqlclient-dev
    postgresql redis-server nginx restic curl jq openssl ca-certificates)
SYSTEMD_DIR=${JFCTL_SYSTEMD_DIR:-/etc/systemd/system}

_entry_units() {
    local units=("${NATIVE_ENTRY_UNITS[@]}")
    [ "${JF_TLS:-}" = caddy ] && units+=(caddy.service)
    printf '%s\n' "${units[@]}"
}

ad_install_packages() {
    local pkgs=("${NATIVE_PACKAGES[@]}")
    [ "$JF_TLS" = caddy ] && pkgs+=(caddy)
    step "Debian-Pakete installieren"
    DEBIAN_FRONTEND=noninteractive apt-get update -q
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends "${pkgs[@]}"
    # Debian enables its own nginx site on port 80; JF-Manager runs a dedicated
    # instance (jf-manager-nginx.service) and Caddy owns port 80/443.
    if systemctl is-enabled nginx.service >/dev/null 2>&1; then
        systemctl disable --now nginx.service >/dev/null 2>&1 || true
        ok "Debian-Standarddienst nginx.service deaktiviert (eigene Instanz jf-manager-nginx)"
    fi
    systemctl enable --now postgresql.service redis-server.service >/dev/null
}

ad_preflight() {
    local failed=0 id version
    id=$(. /etc/os-release 2>/dev/null && echo "${ID:-}")
    version=$(. /etc/os-release 2>/dev/null && echo "${VERSION_ID:-}")
    if [ "$id" = debian ] && [ "$version" = 13 ]; then
        ok "Debian 13 erkannt"
    elif [ -n "${JFCTL_ALLOW_UNSUPPORTED_OS:-}" ]; then
        warn "Nicht unterstütztes System ($id $version) – nur für Tests freigegeben (JFCTL_ALLOW_UNSUPPORTED_OS)"
    else
        err "Nativer Betrieb setzt Debian 13 voraus (gefunden: ${id:-unbekannt} ${version:-})"; failed=1
    fi
    if [ "$(dpkg --print-architecture 2>/dev/null)" = amd64 ] || [ -n "${JFCTL_ALLOW_UNSUPPORTED_OS:-}" ]; then
        ok "Architektur $(dpkg --print-architecture 2>/dev/null || uname -m)"
    else
        err "Referenzplattform ist amd64 (gefunden: $(dpkg --print-architecture 2>/dev/null || uname -m))"; failed=1
    fi
    if have systemctl && [ -d /run/systemd/system ]; then ok "systemd aktiv"; else err "systemd läuft nicht"; failed=1; fi
    if have docker && [ -z "${JFCTL_ALLOW_UNSUPPORTED_OS:-}" ]; then
        warn "Docker ist installiert; der native Weg nutzt es nicht."
    fi
    return $failed
}

_render_tmpl() { # src dst
    sed -e "s#@ETC@#$JF_ETC#g" -e "s#@OPT@#$JF_OPT#g" -e "s#@DATA@#$JF_DATA_DIR#g" "$1" >"$2"
}

_native_env() {
    local pw tmp
    pw=$(kv_get "$JF_SECRETS_ENV" POSTGRES_PASSWORD) || die "$EX_ERROR" "POSTGRES_PASSWORD fehlt in $JF_SECRETS_ENV"
    tmp=$(mktemp "$JF_ETC/native.env.XXXXXX"); chmod 600 "$tmp"
    {
        echo "# Erzeugt von jfctl – nicht von Hand ändern."
        echo "DATABASE_URL=$(kv_quote "postgres://jf_manager:$pw@127.0.0.1:5432/jf_manager")"
        echo "REDIS_URL=redis://127.0.0.1:6379/0"
        echo "STATIC_ROOT=$(kv_quote "$JF_DATA_DIR/static")"
        echo "STATIC_URL=/static/"
        echo "MEDIA_ROOT=$(kv_quote "$JF_DATA_DIR/uploads")"
        echo "MEDIA_URL=/uploads/"
    } >"$tmp"
    mv -f "$tmp" "$JF_ETC/native.env"
}

_render_nginx() {
    local src="$JF_OPT/current/frontend" dst="$JF_ETC/nginx" bind
    bind=127.0.0.1:8080
    [ "$JF_TLS" = proxy ] && bind=$JF_HTTP_BIND
    mkdir -p "$dst/conf.d" "$dst/snippets"
    sed -e '1i user www-data;' \
        -e 's#^pid .*#pid /run/jf-manager-nginx.pid;#' \
        -e "s#/var/log/nginx/error.log#$JF_LOG_DIR/nginx-error.log#" \
        -e "s#/var/log/nginx/access.log#$JF_LOG_DIR/nginx-access.log#" \
        -e "s#include /etc/nginx/conf.d/\*.conf;#include $dst/conf.d/*.conf;#" \
        -e "s#/etc/nginx/trusted-proxies.conf#$JF_TRUSTED_PROXIES#" \
        "$src/nginx.conf" >"$dst/nginx.conf"
    sed -e 's#server backend:8000;#server 127.0.0.1:8000;#' \
        -e "s#listen 8080;#listen $bind;#" \
        -e "s#alias /static/;#alias $JF_DATA_DIR/static/;#" \
        -e "s#root /usr/share/nginx/html;#root $JF_OPT/current/frontend/dist;#g" \
        -e "s#/etc/nginx/snippets/#$dst/snippets/#g" \
        "$src/conf.d/default.conf" >"$dst/conf.d/default.conf"
    local snippet
    for snippet in "$src"/snippets/*.conf; do
        sed -e "s#/etc/nginx/snippets/#$dst/snippets/#g" "$snippet" >"$dst/snippets/$(basename "$snippet")"
    done
    # Fail loudly when the shared configuration changed shape.
    grep -q 'server 127.0.0.1:8000;' "$dst/conf.d/default.conf" &&
        grep -q "listen $bind;" "$dst/conf.d/default.conf" &&
        grep -q 'pid /run/jf-manager-nginx.pid;' "$dst/nginx.conf" ||
        die "$EX_ERROR" "Nginx-Konfiguration ließ sich nicht für den nativen Betrieb anpassen."
    if have nginx; then nginx -t -q -c "$dst/nginx.conf" || die "$EX_ERROR" "nginx -t meldet Fehler."; fi
}

_render_caddy() {
    [ "$JF_TLS" = caddy ] || return 0
    mkdir -p /etc/caddy
    sed -e "s#@DOMAIN@#$JF_DOMAIN#g" -e "s#@ACME_EMAIL@#${JF_ACME_EMAIL:-admin@$JF_DOMAIN}#g" \
        "$JF_OPT/current/ops/native/Caddyfile.tmpl" >/etc/caddy/Caddyfile
}

ad_render() {
    local unit
    id -u "$JF_SERVICE_USER" >/dev/null 2>&1 ||
        useradd --system --home-dir "$JF_DATA_DIR" --no-create-home --shell /usr/sbin/nologin "$JF_SERVICE_USER"
    mkdir -p "$JF_DATA_DIR"/{uploads,static} "$JF_LOG_DIR"
    chown "$JF_SERVICE_USER:$JF_SERVICE_USER" "$JF_DATA_DIR/uploads" "$JF_DATA_DIR/static"
    chmod 750 "$JF_DATA_DIR/uploads"; chmod 755 "$JF_DATA_DIR" "$JF_DATA_DIR/static"
    _native_env
    render_trusted_proxies native
    _render_nginx
    _render_caddy
    for unit in "$JF_OPT"/current/ops/native/systemd/*; do
        _render_tmpl "$unit" "$SYSTEMD_DIR/$(basename "$unit")"
    done
    systemctl daemon-reload
    systemctl enable jf-manager.target "${NATIVE_APP_UNITS[@]}" "${NATIVE_ENTRY_UNITS[@]}" >/dev/null 2>&1
    if [ "$JF_TLS" = caddy ]; then systemctl enable caddy.service >/dev/null 2>&1; fi
}

ad_db_start() { systemctl start postgresql.service redis-server.service; }

# Creates the database role/database (idempotent); password from secrets.env.
ad_db_init() {
    local pw
    pw=$(kv_get "$JF_SECRETS_ENV" POSTGRES_PASSWORD)
    ad_db_start
    if [ "$(_pg -tAc "SELECT 1 FROM pg_roles WHERE rolname='jf_manager'")" != 1 ]; then
        _pg -c "CREATE ROLE jf_manager LOGIN" >/dev/null
    fi
    # Password via stdin, never as process argument.
    printf "ALTER ROLE jf_manager PASSWORD '%s';\n" "$pw" | _pg >/dev/null
    if [ "$(_pg -tAc "SELECT 1 FROM pg_database WHERE datname='jf_manager'")" != 1 ]; then
        _pg -c "CREATE DATABASE jf_manager OWNER jf_manager" >/dev/null
    fi
}

_pg() { runuser -u postgres -- psql -v ON_ERROR_STOP=1 -q -d postgres "$@"; }

ad_start() {
    systemctl start postgresql.service redis-server.service
    if workers_held; then
        systemctl start jf-manager-web.service "${NATIVE_ENTRY_UNITS[@]}"
        mapfile -t entry < <(_entry_units); systemctl start "${entry[@]}"
        warn "Worker bleiben angehalten (nach Restore). Prüfen und freigeben: jfctl workers release"
    else
        systemctl start jf-manager.target
        mapfile -t entry < <(_entry_units); systemctl start "${entry[@]}"
    fi
}

ad_stop() {
    local entry
    mapfile -t entry < <(_entry_units)
    systemctl stop "${entry[@]}" "${NATIVE_APP_UNITS[@]}" jf-manager.target
}

ad_status() {
    local unit
    for unit in postgresql.service redis-server.service "${NATIVE_APP_UNITS[@]}" $(_entry_units); do
        printf '%-28s %s\n' "$unit" "$(systemctl is-active "$unit" 2>/dev/null || true)"
    done
}

ad_logs() {
    local units=() args=(--no-pager -n "${JF_LOG_LINES:-200}") u
    if [ $# -gt 0 ]; then for u in "$@"; do units+=(-u "jf-manager-$u.service"); done
    else for u in "${NATIVE_APP_UNITS[@]}" "${NATIVE_ENTRY_UNITS[@]}"; do units+=(-u "$u"); done; fi
    [ "${JF_FOLLOW:-0}" = 1 ] && args+=(-f)
    journalctl "${units[@]}" "${args[@]}" | while IFS= read -r line; do printf '%s\n' "$(redact "$line")"; done
}

# manage.py as service user with the service environment. Files are parsed,
# not sourced, and values are exported inside a subshell: passing them as
# "env KEY=VALUE" arguments would expose secrets in /proc/<pid>/cmdline.
ad_manage() {
    (
        local v f k runuser_bin
        runuser_bin=$(command -v runuser) || exit 1
        while read -r v; do
            case $v in JF_ADMIN_USER|JF_ADMIN_EMAIL|JF_ADMIN_PASSWORD|JF_ADMIN_FORCE|JF_RESET_MFA) ;; *) unset "$v" ;; esac
        done < <(compgen -e)
        export PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
            DJANGO_SETTINGS_MODULE=jf_manager_backend.docker_settings
        for f in "$JF_APP_ENV" "$JF_ETC/native.env"; do
            while IFS= read -r k; do export "$k=$(kv_get "$f" "$k")"; done < <(kv_keys "$f")
        done
        cd "$JF_OPT/current/backend" || exit 1
        exec "$runuser_bin" -u "$JF_SERVICE_USER" -- "$JF_OPT/current/venv/bin/python" manage.py "$@"
    )
}

ad_entry_stop()  { local e; mapfile -t e < <(_entry_units); systemctl stop "${e[@]}"; }
ad_entry_start() { local e; mapfile -t e < <(_entry_units); systemctl start "${e[@]}"; }
ad_app_stop()    { ad_entry_stop; systemctl stop "${NATIVE_APP_UNITS[@]}"; }
ad_app_start()   { systemctl start jf-manager-web.service; workers_held || systemctl start "${NATIVE_WORKER_UNITS[@]}"; }
ad_workers_stop()  { systemctl stop "${NATIVE_WORKER_UNITS[@]}"; }
ad_workers_start() { systemctl start "${NATIVE_WORKER_UNITS[@]}"; }

ad_health_internal() {
    local i
    for i in $(seq 1 "${1:-60}"); do
        curl -fsS -o /dev/null http://127.0.0.1:8000/health/ 2>/dev/null && return 0
        sleep 2
    done
    return 1
}

ad_health_entry() {
    local i bind=127.0.0.1:8080
    [ "$JF_TLS" = proxy ] && bind=${JF_HTTP_BIND/0.0.0.0/127.0.0.1}
    for i in $(seq 1 "${1:-30}"); do
        curl -fsS -o /dev/null "http://$bind/health" 2>/dev/null && return 0
        sleep 2
    done
    return 1
}

ad_worker_running() {
    local u
    for u in "${NATIVE_WORKER_UNITS[@]}"; do systemctl is-active --quiet "$u" || return 1; done
}

ad_psql() { _pg -tA -d "${2:-postgres}" -c "$1"; }

ad_pg_major() { _pg -tAc 'SHOW server_version_num' | awk '{print int($1/10000)}'; }

ad_db_dump() { runuser -u postgres -- pg_dump -d jf_manager -Fc --no-owner --no-acl >"$1"; }

ad_db_restore_into() { # database file
    ad_psql "DROP DATABASE IF EXISTS \"$1\"" >/dev/null
    ad_psql "CREATE DATABASE \"$1\" OWNER jf_manager" >/dev/null
    # Objects belong to the application role, as in the Compose installation.
    runuser -u postgres -- pg_restore -d "$1" --no-owner --no-acl --role=jf_manager --exit-on-error <"$2"
}

ad_redis_flush_queues() { redis-cli -h 127.0.0.1 FLUSHALL >/dev/null; }

ad_uploads_dir() { printf '%s' "$JF_DATA_DIR/uploads"; }
ad_uploads_owner() { printf '%s:%s' "$JF_SERVICE_USER" "$JF_SERVICE_USER"; }

# Builds the Python environment inside the (already verified and extracted)
# release directory. Locked packages with hashes only.
# jfctl runs with umask 027; release files must be readable (not writable) for
# the service user and for nginx (www-data).
_native_perms() {
    chmod 755 "$JF_OPT" "$JF_OPT/releases" 2>/dev/null || true
    chmod -R u+rwX,go+rX,go-w "$1"
}

ad_fetch_release() { # version manifest
    local dir="$JF_OPT/releases/${1#v}"
    if [ -x "$dir/venv/bin/python" ] && [ -f "$dir/venv/.complete" ]; then _native_perms "$dir"; return 0; fi
    rm -rf "$dir/venv"
    python3 -m venv "$dir/venv"
    "$dir/venv/bin/pip" install -q --disable-pip-version-check --no-cache-dir --require-hashes \
        -r "$dir/backend/requirements.lock.txt" || return 1
    "$dir/venv/bin/pip" install -q --disable-pip-version-check --no-cache-dir --require-hashes \
        -r "$dir/backend/requirements-server.txt" || return 1
    touch "$dir/venv/.complete"
    _native_perms "$dir"
}

# The caller switched /opt/jf-manager/current; units point to "current".
ad_activate_release() { JF_VERSION=$1; ad_render; }

ad_running_version() { readlink "$JF_OPT/current" 2>/dev/null | xargs -r basename; }

ad_timers_runner() { printf '%s' native; }
