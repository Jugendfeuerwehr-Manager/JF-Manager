#!/bin/sh
# Abgelöst durch jfctl (OPS-05). Siehe docs/operations/ops-migration.md.
echo "healthcheck.sh wird nicht mehr unterstützt." >&2
echo "Nachfolger: jfctl status  bzw.  jfctl doctor" >&2
echo "Übernahme bestehender Installationen: docs/operations/ops-migration.md" >&2
exit 2
