"""Collect Content-Security-Policy violation reports during the report-only rollout.

Reports are anonymous and untrusted. Only the directive, the origin of the
blocked resource and the page path are logged; query strings and full URLs can
carry personal data and are dropped.
"""

import json
import logging
import time
from urllib.parse import urlsplit

from django.core.cache import cache
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger("security.csp")

MAX_BODY_BYTES = 16 * 1024
MAX_REPORTS_PER_REQUEST = 10
# Behind the bundled Nginx every client shares one address, so the limit is global.
MAX_REPORTS_PER_MINUTE = 120
KEYWORD_SOURCES = {"inline", "eval", "self", "data", "blob", "wasm-eval", "trusted-types-policy"}


def _origin(value):
    if not isinstance(value, str) or not value:
        return "-"
    if value in KEYWORD_SOURCES:
        return value
    parts = urlsplit(value)
    if parts.scheme in {"http", "https", "ws", "wss"} and parts.netloc:
        return f"{parts.scheme}://{parts.netloc}"
    return (parts.scheme or value)[:20]


def _path(value):
    return urlsplit(value).path[:200] if isinstance(value, str) and value else "-"


def _reports(payload):
    """Legacy `report-uri` bodies and Reporting API batches."""
    if isinstance(payload, dict) and isinstance(payload.get("csp-report"), dict):
        return [payload["csp-report"]]
    if isinstance(payload, list):
        return [
            entry["body"]
            for entry in payload
            if isinstance(entry, dict) and entry.get("type") == "csp-violation" and isinstance(entry.get("body"), dict)
        ]
    return []


def _within_rate_limit():
    key = f"csp-report:{int(time.time() // 60)}"
    cache.add(key, 0, timeout=120)
    try:
        return cache.incr(key) <= MAX_REPORTS_PER_MINUTE
    except ValueError:
        return True


@csrf_exempt
@require_POST
def csp_report(request):
    try:
        declared_length = int(request.META.get("CONTENT_LENGTH") or 0)
    except ValueError:
        return HttpResponse(status=400)
    if declared_length > MAX_BODY_BYTES:
        return HttpResponse(status=413)
    if not _within_rate_limit():
        return HttpResponse(status=204)
    try:
        payload = json.loads(request.body[:MAX_BODY_BYTES])
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)
    for report in _reports(payload)[:MAX_REPORTS_PER_REQUEST]:
        logger.warning(
            "CSP violation: directive=%s blocked=%s page=%s",
            str(
                report.get("effective-directive")
                or report.get("effectiveDirective")
                or report.get("violated-directive")
                or "-"
            )[:60],
            _origin(report.get("blocked-uri") or report.get("blockedURL")),
            _path(report.get("document-uri") or report.get("documentURL")),
        )
    return HttpResponse(status=204)
