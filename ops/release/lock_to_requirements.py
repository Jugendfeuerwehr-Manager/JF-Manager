#!/usr/bin/env python3
"""Convert backend/Pipfile.lock ("default" section) into a pip requirements
file with hashes, so native installs use exactly the locked packages
(pip install --require-hashes). Usage: lock_to_requirements.py LOCK OUT"""

import json
import sys


def main(lock_path: str, out_path: str) -> int:
    with open(lock_path, encoding="utf-8") as handle:
        lock = json.load(handle)
    lines = ["# Generated from backend/Pipfile.lock by ops/release/lock_to_requirements.py"]
    for name, spec in sorted(lock.get("default", {}).items()):
        version = spec.get("version")
        hashes = spec.get("hashes", [])
        if not version or not hashes:
            print(f"{name}: no pinned version/hashes in lock file", file=sys.stderr)
            return 1
        requirement = f"{name}{version}"
        if spec.get("markers"):
            requirement += f" ; {spec['markers']}"
        lines.append(requirement + " \\")
        lines.extend(f"    --hash={digest} \\" for digest in hashes[:-1])
        lines.append(f"    --hash={hashes[-1]}")
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
