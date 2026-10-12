#!/usr/bin/env bash
# Print the CHANGELOG.md section of one version (without its heading) for the release notes.
# Usage: ops/release/changelog-notes.sh <version> [changelog]
# Exit 1 when the version has no section, so the caller can fall back or fail.
set -euo pipefail

version="${1:?Version fehlt, z. B. 3.2.1}"
version="${version#v}"
changelog="${2:-CHANGELOG.md}"

[[ -f $changelog ]] || { echo "Änderungsprotokoll $changelog fehlt" >&2; exit 1; }

section="$(awk -v version="$version" '
  /^## \[/ {
    if (found) exit
    found = index($0, "## [" version "]") == 1
    next
  }
  found { print }
' "$changelog")"

# Trim leading and trailing blank lines.
section="$(printf '%s\n' "$section" | sed -e '/./,$!d' | sed -e ':a' -e '/^\n*$/{$d;N;ba' -e '}')"

[[ -n $section ]] || { echo "Kein Abschnitt für Version $version in $changelog" >&2; exit 1; }
printf '%s\n' "$section"
