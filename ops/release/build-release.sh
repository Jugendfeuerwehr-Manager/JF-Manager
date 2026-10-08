#!/usr/bin/env bash
# Builds the release package used by both production modes (OPS-01.2):
#   jf-manager-<version>.tar.gz   ops/, backend/ (committed files only),
#                                 frontend/ (built SPA), MANIFEST.json
#   release-manifest.json         version, commit, image digests, tarball hash
#   SHA256SUMS                    checksums of both files
#
# Usage: ops/release/build-release.sh --version 1.4.0 --out dist/release \
#          [--backend-image ref@sha256:…] [--frontend-image ref@sha256:…] \
#          [--frontend-dist path/to/dist] [--ref HEAD|WORKTREE]
# --ref WORKTREE packs the working tree (tracked and new, not ignored files);
# only for local tests, never for published releases.
set -Eeuo pipefail

version="" out="" backend_image="" frontend_image="" frontend_dist="" ref=HEAD
while [ $# -gt 0 ]; do
    case $1 in
        --version) version=${2#v}; shift 2 ;;
        --out) out=$2; shift 2 ;;
        --backend-image) backend_image=$2; shift 2 ;;
        --frontend-image) frontend_image=$2; shift 2 ;;
        --frontend-dist) frontend_dist=$2; shift 2 ;;
        --ref) ref=$2; shift 2 ;;
        *) echo "Unbekannte Option: $1" >&2; exit 2 ;;
    esac
done
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || { echo "--version X.Y.Z erforderlich" >&2; exit 2; }
[ -n "$out" ] || { echo "--out erforderlich" >&2; exit 2; }

repo=$(git rev-parse --show-toplevel)
if [ "$ref" = WORKTREE ]; then
    commit="$(git -C "$repo" rev-parse HEAD)-worktree"
    commit_time=$(date +%s)
else
    commit=$(git -C "$repo" rev-parse "$ref")
    commit_time=$(git -C "$repo" log -1 --format=%ct "$commit")
fi

# export_paths DEST PATH... -> copies committed (or working tree) files
export_paths() {
    local dest=$1; shift
    if [ "$ref" = WORKTREE ]; then
        (cd "$repo" && git ls-files -co --exclude-standard -- "$@" | tar -cf - -T -) | tar -x -C "$dest"
    else
        git -C "$repo" archive "$commit" "$@" | tar -x -C "$dest"
    fi
}
name="jf-manager-$version"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
stage="$work/$name"
mkdir -p "$stage" "$out"

# Committed sources only: no local edits, secrets or build leftovers.
export_paths "$stage" ops backend
rm -rf "$stage/backend/.env" "$stage/backend/db.sqlite3"

python3 "$repo/ops/release/lock_to_requirements.py" \
    "$stage/backend/Pipfile.lock" "$stage/backend/requirements.lock.txt"

if [ -z "$frontend_dist" ]; then
    export_paths "$work" frontend
    (cd "$work/frontend" && npm ci --no-audit --no-fund && VITE_API_BASE_URL=/api/v1 npm run build-only)
    frontend_dist="$work/frontend/dist"
fi
[ -f "$frontend_dist/index.html" ] || { echo "Frontend-Build fehlt: $frontend_dist/index.html" >&2; exit 1; }
mkdir -p "$stage/frontend"
cp -a "$frontend_dist" "$stage/frontend/dist"
# Nginx configuration shared with the frontend image (native mode renders it).
export_paths "$stage" frontend/nginx.conf frontend/conf.d/default.conf \
    frontend/snippets frontend/trusted-proxies.conf

python_req=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["_meta"]["requires"]["python_version"])' "$stage/backend/Pipfile.lock")
created=$(date -u -d "@$commit_time" +%Y-%m-%dT%H:%M:%SZ)

jq -n --arg version "$version" --arg commit "$commit" --arg created "$created" \
    --arg python "$python_req" --arg backend "$backend_image" --arg frontend "$frontend_image" \
    '{format: 1, product: "jf-manager", version: $version, commit: $commit, created: $created,
      python: $python, postgres_major: 17,
      images: {backend: $backend, frontend: $frontend}}' >"$stage/MANIFEST.json"

tarball="$out/$name.tar.gz"
tar --sort=name --mtime="@$commit_time" --owner=0 --group=0 --numeric-owner \
    -C "$work" -cf - "$name" | gzip -n -9 >"$tarball"

sha=$(sha256sum "$tarball" | awk '{print $1}')
jq --arg file "$name.tar.gz" --arg sha "$sha" '. + {tarball: {file: $file, sha256: $sha}}' \
    "$stage/MANIFEST.json" >"$out/release-manifest.json"
(cd "$out" && sha256sum "$name.tar.gz" release-manifest.json >SHA256SUMS)

echo "Release $version ($commit) erstellt:"
cat "$out/SHA256SUMS"
