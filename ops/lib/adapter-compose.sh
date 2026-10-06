# shellcheck shell=bash
# Docker Compose adapter. Implements the adapter interface used by jfctl:
#   ad_preflight, ad_render, ad_start, ad_stop, ad_status, ad_logs, ad_manage,
#   ad_entry_stop|start, ad_app_stop|start, ad_workers_stop|start,
#   ad_health_internal, ad_db_*, ad_fetch_release, ad_activate_release,
#   ad_redis_flush_queues, ad_running_version, ad_install_packages

JF_COMPOSE_PROJECT=${JF_COMPOSE_PROJECT:-jf-manager}
APP_SERVICES=(backend worker push-worker)
WORKER_SERVICES=(worker push-worker)

_entry_services() { printf '%s\n' frontend; [ "${JF_TLS:-}" = caddy ] && printf '%s\n' caddy; return 0; }

_compose_file() { printf '%s' "${JF_COMPOSE_FILE:-$JF_OPT/current/ops/compose/compose.yml}"; }

dc() {
    local profile=()
    [ "${JF_TLS:-}" = caddy ] && profile=(--profile tls)
    docker compose -p "$JF_COMPOSE_PROJECT" -f "$(_compose_file)" --env-file "$JF_COMPOSE_ENV" "${profile[@]}" "$@"
}

ad_install_packages() {
    have docker && docker compose version >/dev/null 2>&1 && have restic && return 0
    if have apt-get; then
        step "Pakete installieren (Docker Engine mit Compose V2, Restic)"
        DEBIAN_FRONTEND=noninteractive apt-get update -q
        if ! have docker; then
            DEBIAN_FRONTEND=noninteractive apt-get install -y -q docker.io docker-compose-v2 ||
                DEBIAN_FRONTEND=noninteractive apt-get install -y -q docker.io docker-compose-plugin
        fi
        DEBIAN_FRONTEND=noninteractive apt-get install -y -q restic curl openssl jq ca-certificates
    else
        die "$EX_PRECHECK" "Docker mit Compose V2 und Restic bitte zuerst installieren."
    fi
}

ad_preflight() {
    local failed=0
    if have docker; then ok "Docker vorhanden"; else err "Docker fehlt"; failed=1; fi
    if docker compose version >/dev/null 2>&1; then
        ok "Docker Compose V2 ($(docker compose version --short 2>/dev/null))"
    else
        err "Docker Compose V2 (docker compose) fehlt; Compose V1 (docker-compose) wird nicht unterstützt"; failed=1
    fi
    if docker info >/dev/null 2>&1; then ok "Docker-Dienst läuft"; else err "Docker-Dienst nicht erreichbar"; failed=1; fi
    return $failed
}

# Writes compose.env and trusted-proxies.conf from jfctl.conf + secrets.env.
ad_render() {
    local pw tmp
    pw=$(kv_get "$JF_SECRETS_ENV" POSTGRES_PASSWORD) || die "$EX_ERROR" "POSTGRES_PASSWORD fehlt in $JF_SECRETS_ENV"
    tmp=$(mktemp "$JF_COMPOSE_ENV.XXXXXX"); chmod 600 "$tmp"
    {
        echo "# Erzeugt von jfctl – nicht von Hand ändern (jfctl config)."
        echo "JF_VERSION=$(kv_quote "${JF_VERSION#v}")"
        echo "JF_BACKEND_IMAGE=$(kv_quote "$JF_BACKEND_IMAGE")"
        echo "JF_FRONTEND_IMAGE=$(kv_quote "$JF_FRONTEND_IMAGE")"
        echo "JF_DATA_DIR=$(kv_quote "$JF_DATA_DIR")"
        echo "JF_APP_ENV=$(kv_quote "$JF_APP_ENV")"
        echo "JF_TRUSTED_PROXIES_FILE=$(kv_quote "$JF_TRUSTED_PROXIES")"
        echo "JF_POSTGRES_MAJOR=$(kv_quote "$JF_POSTGRES_MAJOR")"
        echo "JF_DOMAIN=$(kv_quote "${JF_DOMAIN:-localhost}")"
        echo "JF_ACME_EMAIL=$(kv_quote "${JF_ACME_EMAIL:-admin@${JF_DOMAIN:-localhost}}")"
        if [ "$JF_TLS" = caddy ]; then echo "JF_HTTP_BIND=127.0.0.1:8080"; else echo "JF_HTTP_BIND=$(kv_quote "$JF_HTTP_BIND")"; fi
        echo "POSTGRES_PASSWORD=$(kv_quote "$pw")"
    } >"$tmp"
    mv -f "$tmp" "$JF_COMPOSE_ENV"
    render_trusted_proxies compose
    mkdir -p "$JF_DATA_DIR"/{uploads,postgres,redis,caddy}
    # uploads belong to the container user django (uid 1000, gid 2000)
    chown 1000:2000 "$JF_DATA_DIR/uploads" 2>/dev/null || true
    chmod 750 "$JF_DATA_DIR/uploads"
}

_images_for_version() { # -> backend and frontend reference for compose.env
    printf '%s:%s %s:%s' "$JF_BACKEND_IMAGE" "${JF_VERSION#v}" "$JF_FRONTEND_IMAGE" "${JF_VERSION#v}"
}

ad_start() {
    if workers_held; then
        local entry; mapfile -t entry < <(_entry_services)
        dc up -d --remove-orphans db redis backend "${entry[@]}"
        dc stop "${WORKER_SERVICES[@]}" >/dev/null 2>&1 || true
        warn "Worker bleiben angehalten (nach Restore). Prüfen und freigeben: jfctl workers release"
    else
        dc up -d --remove-orphans
    fi
}

ad_stop() { dc stop; }

ad_status() { dc ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'; }

ad_logs() { # [service] [-f]
    local args=(--tail "${JF_LOG_LINES:-200}")
    [ "${JF_FOLLOW:-0}" = 1 ] && args+=(-f)
    dc logs "${args[@]}" "$@" | while IFS= read -r line; do printf '%s\n' "$(redact "$line")"; done
}

# One-off management command in a fresh backend container (works while the
# web service is stopped). No static collection, no migration on entry.
ad_manage() {
    dc run --rm --no-deps -T -e DJANGO_COLLECTSTATIC=off backend python manage.py "$@"
}

ad_entry_stop()  { local e; mapfile -t e < <(_entry_services); dc stop "${e[@]}" >/dev/null; }
ad_entry_start() { local e; mapfile -t e < <(_entry_services); dc up -d --no-deps "${e[@]}" >/dev/null; }
ad_app_stop()    { dc stop frontend "${APP_SERVICES[@]}" >/dev/null; }
ad_app_start()   { dc up -d --no-deps backend >/dev/null; workers_held || dc up -d --no-deps "${WORKER_SERVICES[@]}" >/dev/null; }
ad_workers_stop()  { dc stop "${WORKER_SERVICES[@]}" >/dev/null; }
ad_workers_start() { dc up -d --no-deps "${WORKER_SERVICES[@]}" >/dev/null; }
ad_db_start()    { dc up -d --wait db redis >/dev/null; }

ad_health_internal() { # backend reachable without going through nginx
    local i
    for i in $(seq 1 "${1:-60}"); do
        if dc exec -T backend curl -fsS -o /dev/null http://localhost:8000/health/ 2>/dev/null; then return 0; fi
        sleep 2
    done
    return 1
}

ad_health_entry() {
    local i
    for i in $(seq 1 "${1:-30}"); do
        if dc exec -T frontend wget -q -O /dev/null http://localhost:8080/health 2>/dev/null; then return 0; fi
        sleep 2
    done
    return 1
}

ad_worker_running() {
    local svc state
    for svc in "${WORKER_SERVICES[@]}"; do
        state=$(dc ps --format '{{.State}}' "$svc" 2>/dev/null || true)
        [ "$state" = running ] || return 1
    done
}

ad_psql() { # SQL on the maintenance database "postgres"
    dc exec -T db psql -v ON_ERROR_STOP=1 -U jf_manager -d "${2:-postgres}" -tAc "$1"
}

ad_pg_major() { dc exec -T db psql -U jf_manager -d postgres -tAc 'SHOW server_version_num' | awk '{print int($1/10000)}'; }

ad_db_dump() { # file (custom format)
    dc exec -T db pg_dump -U jf_manager -d jf_manager -Fc --no-owner --no-acl >"$1"
}

ad_db_restore_into() { # database file
    ad_psql "DROP DATABASE IF EXISTS \"$1\"" >/dev/null
    ad_psql "CREATE DATABASE \"$1\" OWNER jf_manager" >/dev/null
    dc exec -T db pg_restore -U jf_manager -d "$1" --no-owner --no-acl --exit-on-error <"$2"
}

ad_redis_flush_queues() {
    # Drop queued RQ jobs and cached data (sessions live in PostgreSQL).
    dc exec -T redis redis-cli FLUSHALL >/dev/null
}

ad_uploads_dir() { printf '%s' "$JF_DATA_DIR/uploads"; }
ad_uploads_owner() { printf '1000:2000'; }

ad_fetch_release() { # version -> pulls images (pinned by digest when the manifest has one)
    local version=$1 manifest=$2 b f
    if [ "$JF_IMAGE_SOURCE" = local ]; then
        docker image inspect "$JF_BACKEND_IMAGE:${version#v}" "$JF_FRONTEND_IMAGE:${version#v}" >/dev/null ||
            die "$EX_PRECHECK" "Lokale Images für $version fehlen (JF_IMAGE_SOURCE=local)."
        return 0
    fi
    b=$(jq -r '.images.backend // empty' "$manifest")
    f=$(jq -r '.images.frontend // empty' "$manifest")
    [ -n "$b" ] && [ -n "$f" ] || die "$EX_PRECHECK" "Releasemanifest enthält keine Imagereferenzen."
    docker pull -q "$b" >/dev/null && docker pull -q "$f" >/dev/null || return 1
    # Tag the verified digests with the version so compose.env stays readable.
    docker tag "$b" "$JF_BACKEND_IMAGE:${version#v}"
    docker tag "$f" "$JF_FRONTEND_IMAGE:${version#v}"
}

ad_activate_release() { # version -> render + recreate containers with the new images
    JF_VERSION=$1
    ad_render
    dc up -d --no-deps --no-start backend worker push-worker frontend >/dev/null
}

ad_running_version() { kv_get "$JF_COMPOSE_ENV" JF_VERSION || true; }

ad_static_refresh() { :; } # collectstatic runs on backend start

ad_timers_runner() { printf '%s' "compose"; }
