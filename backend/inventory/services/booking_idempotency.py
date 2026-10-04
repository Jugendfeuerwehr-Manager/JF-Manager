"""Durable replay of explicitly keyed stock booking API requests."""

import hashlib
import json

from django.db import transaction
from rest_framework import serializers
from rest_framework.response import Response

from inventory.models import StockBookingRequest


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def run_idempotent_booking(request, callback, *, replay_allowed=None):
    """Run one booking transaction once per user/key; roll back failed attempts."""
    key = request.headers.get("Idempotency-Key")
    if key is None:
        return callback()
    if not isinstance(key, str) or not key.strip() or len(key) > 128:
        raise serializers.ValidationError({"idempotency_key": "Kennung muss 1 bis 128 Zeichen enthalten."})
    key = key.strip()
    payload = {"method": request.method, "path": request.path, "data": request.data}
    fingerprint = hashlib.sha256(_canonical_json(payload).encode()).hexdigest()

    with transaction.atomic():
        booking, created = StockBookingRequest.objects.select_for_update().get_or_create(
            user=request.user,
            key=key,
            defaults={"request_fingerprint": fingerprint},
        )
        if not created:
            if booking.request_fingerprint != fingerprint:
                return Response({"detail": "Idempotenzkennung wurde bereits mit anderem Inhalt verwendet."}, status=409)
            if booking.response_status is None:
                raise serializers.ValidationError({"idempotency_key": "Buchung wird noch verarbeitet."})
            if replay_allowed is not None and not replay_allowed(booking.response_data):
                return Response({"detail": "Kein Zugriff mehr auf diese Buchung."}, status=403)
            return Response(booking.response_data, status=booking.response_status)

        response = callback()
        if response.status_code >= 400:
            booking.delete()
            return response
        booking.response_status = response.status_code
        booking.response_data = json.loads(_canonical_json(response.data))
        booking.save(update_fields=["response_status", "response_data"])
        return response
