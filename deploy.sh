#!/bin/sh
# Abgelöst durch jfctl (OPS-05). Siehe docs/operations/ops-migration.md.
echo "deploy.sh wird nicht mehr unterstützt." >&2
echo "Nachfolger: jfctl update --version X.Y.Z  (docs/operations/ops-backup-restore-update.md)" >&2
echo "Übernahme bestehender Installationen: docs/operations/ops-migration.md" >&2
exit 2
