# shellcheck shell=bash
# Release artifacts: download, verification, extraction, version switch.
# A release consists of jf-manager-<v>.tar.gz, release-manifest.json and
# SHA256SUMS (built by ops/release/build-release.sh in CI).

_download() { # url dest
    curl -fsSL --proto '=https' --tlsv1.2 --retry 3 --retry-delay 2 -o "$2" "$1"
}

# release_fetch VERSION [LOCAL_DIR] -> prints directory with the verified files
release_fetch() {
    local version=${1#v} local_dir=${2:-} dir name
    name="jf-manager-$version.tar.gz"
    dir="$JF_OPT/downloads/$version"
    mkdir -p "$dir"
    if [ -n "$local_dir" ]; then
        cp -f "$local_dir/$name" "$local_dir/release-manifest.json" "$local_dir/SHA256SUMS" "$dir/" ||
            die "$EX_PRECHECK" "Releasedateien für $version fehlen in $local_dir."
    else
        local base="$JF_RELEASE_URL/v$version"
        _download "$base/SHA256SUMS" "$dir/SHA256SUMS" &&
            _download "$base/release-manifest.json" "$dir/release-manifest.json" &&
            _download "$base/$name" "$dir/$name" ||
            die "$EX_PRECHECK" "Release $version konnte nicht geladen werden ($base)."
    fi
    (cd "$dir" && sha256sum --quiet --strict -c SHA256SUMS) ||
        die "$EX_PRECHECK" "Prüfsummen von Release $version stimmen nicht. Nichts geändert."
    [ "$(jq -r .version "$dir/release-manifest.json")" = "$version" ] ||
        die "$EX_PRECHECK" "Releasemanifest gehört nicht zu Version $version."
    [ "$(jq -r .tarball.sha256 "$dir/release-manifest.json")" = "$(sha256sum "$dir/$name" | awk '{print $1}')" ] ||
        die "$EX_PRECHECK" "Releasemanifest und Paket passen nicht zusammen."
    release_verify_provenance "$dir/$name"
    printf '%s' "$dir"
}

# Build provenance (GitHub artifact attestation). "auto" verifies when the gh
# CLI is available, "required" refuses without successful verification,
# "off" skips (e.g. offline installs from a local directory).
release_verify_provenance() {
    local file=$1
    case "${JF_VERIFY_ATTESTATION:-auto}" in
        off) warn "Herkunftsnachweis nicht geprüft (JF_VERIFY_ATTESTATION=off)"; return 0 ;;
        auto|required)
            if have gh; then
                if gh attestation verify "$file" --repo "$JF_GITHUB_REPO" >/dev/null 2>&1; then
                    ok "Herkunftsnachweis (GitHub-Attestierung) bestätigt" >&2; return 0
                fi
                die "$EX_PRECHECK" "Herkunftsnachweis für $(basename "$file") ungültig. Nichts geändert."
            fi
            [ "$JF_VERIFY_ATTESTATION" = required ] &&
                die "$EX_PRECHECK" "JF_VERIFY_ATTESTATION=required, aber gh CLI fehlt."
            warn "gh CLI fehlt: nur Prüfsummen geprüft, Herkunftsnachweis übersprungen" ;;
        *) die "$EX_USAGE" "JF_VERIFY_ATTESTATION muss auto, required oder off sein." ;;
    esac
}

# release_extract DIR VERSION -> $JF_OPT/releases/<version> (idempotent)
release_extract() {
    local dir=$1 version=${2#v} target tmp
    target="$JF_OPT/releases/$version"
    if [ -f "$target/MANIFEST.json" ] && [ "$(jq -r .version "$target/MANIFEST.json")" = "$version" ]; then
        return 0
    fi
    mkdir -p "$JF_OPT/releases"
    tmp=$(mktemp -d "$JF_OPT/releases/.extract.XXXXXX")
    # Paths in the archive are checked before extraction (no absolute or ../ entries).
    if tar -tzf "$dir/jf-manager-$version.tar.gz" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
        rm -rf "$tmp"; die "$EX_PRECHECK" "Releasepaket enthält unzulässige Pfade."
    fi
    tar -xzf "$dir/jf-manager-$version.tar.gz" -C "$tmp" --no-same-owner
    [ -f "$tmp/jf-manager-$version/MANIFEST.json" ] || { rm -rf "$tmp"; die "$EX_PRECHECK" "MANIFEST.json fehlt im Paket."; }
    cp "$dir/release-manifest.json" "$tmp/jf-manager-$version/release-manifest.json"
    rm -rf "$target"
    mv "$tmp/jf-manager-$version" "$target"
    rmdir "$tmp"
    chmod -R go-w "$target"
}

# Atomic switch of /opt/jf-manager/current and /usr/local/sbin/jfctl.
switch_current() {
    local version=${1#v} link="$JF_OPT/current"
    [ -d "$JF_OPT/releases/$version" ] || die "$EX_ERROR" "Release $version ist nicht entpackt."
    ln -sfn "releases/$version" "$link.new"
    mv -Tf "$link.new" "$link"
    if [ -z "${JFCTL_NO_SBIN_LINK:-}" ]; then
        ln -sfn "$JF_OPT/current/ops/jfctl" "${JFCTL_SBIN:-/usr/local/sbin/jfctl}"
    fi
}

# Keep the current, the previous and the newest two other releases.
release_prune() {
    local keep current previous
    current=$(readlink "$JF_OPT/current" 2>/dev/null | xargs -r basename)
    previous=$(kv_get "$JF_STATE_DIR/update.state" PREVIOUS_VERSION 2>/dev/null || true)
    keep=$(find "$JF_OPT/releases" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort -V | tail -n 2)
    find "$JF_OPT/releases" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | while read -r v; do
        [ "$v" = "$current" ] || [ "$v" = "$previous" ] || grep -qx "$v" <<<"$keep" || rm -rf "${JF_OPT:?}/releases/$v" "${JF_OPT:?}/downloads/$v"
    done
}

# Trusted proxy list for nginx (geo syntax).
render_trusted_proxies() {
    local tmp addr
    tmp=$(mktemp "$JF_TRUSTED_PROXIES.XXXXXX")
    {
        echo "# Erzeugt von jfctl ($JF_TLS). Nur diese Absender dürfen X-Forwarded-Proto setzen."
        if [ "$JF_TLS" = caddy ]; then
            echo "127.0.0.1/32 1;"
            echo "::1/128 1;"
            # Compose: Caddy reaches nginx over the edge network.
            [ "$1" = compose ] && echo "$JF_EDGE_SUBNET 1;"
        else
            for addr in $JF_TRUSTED_PROXY_ADDRS; do
                [[ $addr =~ ^[0-9a-fA-F:.]+(/[0-9]{1,3})?$ ]] || die "$EX_USAGE" "Ungültige Proxyadresse: $addr"
                echo "$addr 1;"
                # Compose: a proxy on this host reaches the published port via
                # docker-proxy, i.e. from the gateway of the edge network.
                if [ "$1" = compose ] && [[ $addr =~ ^(127\.|::1) ]]; then echo "$JF_EDGE_SUBNET 1;"; fi
            done
        fi
    } >"$tmp"
    chmod 644 "$tmp"
    mv -f "$tmp" "$JF_TRUSTED_PROXIES"
}

workers_held() { [ -f "$JF_STATE_DIR/workers-held" ]; }
