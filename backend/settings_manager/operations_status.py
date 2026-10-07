"""Read-only view of the status file written by jfctl (OPS-03.4).

The web application never runs host commands; it only reads the public copy
that jfctl writes after install, backup, restore, update and worker changes.
Only whitelisted, length-limited fields leave this module.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

MAX_BYTES = 64 * 1024
STATUS_STALE_AFTER = timedelta(hours=48)
BACKUP_OVERDUE_AFTER = timedelta(hours=36)


def _text(value, limit=200):
    return value[:limit] if isinstance(value, str) else ""


def _time(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)


def _backup(raw):
    if not isinstance(raw, dict):
        return None
    success = raw.get("last_success") if isinstance(raw.get("last_success"), dict) else {}
    return {
        "status": raw.get("status") if raw.get("status") in ("ok", "failed") else "unknown",
        "finished": _text(raw.get("finished"), 40),
        "message": _text(raw.get("message")),
        "last_success": _text(success.get("finished"), 40) or None,
    }


def operations_status(path=None, now=None):
    path = path if path is not None else getattr(settings, "OPS_STATUS_FILE", "")
    if not path:
        return {"available": False, "reason": "not_configured"}
    file = Path(path)
    try:
        if file.stat().st_size > MAX_BYTES:
            return {"available": False, "reason": "unreadable"}
        raw = json.loads(file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"available": False, "reason": "missing"}
    except (OSError, ValueError):
        return {"available": False, "reason": "unreadable"}
    if not isinstance(raw, dict):
        return {"available": False, "reason": "unreadable"}

    now = now or timezone.now()
    backup = _backup(raw.get("last_backup"))
    data = {
        "available": True,
        "instance": _text(raw.get("instance"), 80),
        "mode": raw.get("mode") if raw.get("mode") in ("compose", "native") else "",
        "version": _text(raw.get("version"), 40),
        "workers_held": raw.get("workers_held") is True,
        "updated": _text(raw.get("updated"), 40),
        "last_backup": backup,
        "warnings": [],
    }
    warnings = data["warnings"]
    updated = _time(data["updated"])
    if updated is None or now - updated > STATUS_STALE_AFTER:
        warnings.append({"code": "status_stale", "text": "Der Betriebsstatus ist älter als zwei Tage."})
    if backup is None:
        warnings.append({"code": "backup_missing", "text": "Es ist noch keine Sicherung erfasst."})
    else:
        if backup["status"] == "failed":
            warnings.append({"code": "backup_failed", "text": "Die letzte Sicherung ist fehlgeschlagen."})
        success = _time(backup["last_success"]) or (_time(backup["finished"]) if backup["status"] == "ok" else None)
        if success is None or now - success > BACKUP_OVERDUE_AFTER:
            warnings.append(
                {"code": "backup_overdue", "text": "Seit mehr als 36 Stunden keine erfolgreiche Sicherung."}
            )
    if data["workers_held"]:
        warnings.append(
            {"code": "workers_held", "text": "Hintergrundaufgaben sind angehalten (jfctl workers release)."}
        )
    return data
