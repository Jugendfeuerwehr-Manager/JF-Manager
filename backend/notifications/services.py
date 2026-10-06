"""Durable outbox: requests only enqueue; the worker performs network I/O."""

import json
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from settings_manager.push_configuration import effective_push

from .models import PushDelivery, PushSubscription
from .validation import validate_endpoint

logger = logging.getLogger(__name__)


def can_read(user, obj, permission):
    if not user.is_active:
        return False
    if user.is_superuser or user.is_staff or user.has_perm("departments.can_access_all_departments"):
        return True
    if obj.department_id is None:
        return False
    roles = user.department_roles.filter(department_id=obj.department_id)
    if not roles.exists():
        return False
    app_label, codename = permission.split(".")
    return (
        user.has_perm(permission)
        or roles.filter(
            groups__permissions__codename=codename, groups__permissions__content_type__app_label=app_label
        ).exists()
    )


def event_object(kind, object_id):
    if kind == "services":
        from servicebook.models import Service

        return Service.objects.filter(pk=object_id).first(), "servicebook.view_service"
    from orders.models import Order

    return Order.objects.filter(pk=object_id).first(), "orders.view_order"


def enqueue_event(kind, object_id):
    if not effective_push()["enabled"]:
        return
    obj, permission = event_object(kind, object_id)
    if not obj:
        return
    for subscription in PushSubscription.objects.filter(**{kind: True}, user__is_active=True).select_related("user"):
        if can_read(subscription.user, obj, permission):
            # Coalesce rapid edits of the same object for this device.
            PushDelivery.objects.get_or_create(subscription=subscription, kind=kind, object_id=object_id)


def deliver_pending(limit=100):
    config = effective_push(include_secret=True)
    if not config["enabled"]:
        return 0
    from pywebpush import WebPushException, webpush

    processed = 0
    ids = list(
        PushDelivery.objects.filter(available_at__lte=timezone.now())
        .order_by("pk")
        .values_list("pk", flat=True)[:limit]
    )
    for delivery_id in ids:
        with transaction.atomic():
            delivery = (
                PushDelivery.objects.select_for_update()
                .filter(pk=delivery_id, available_at__lte=timezone.now())
                .first()
            )
            if not delivery:
                continue
            # Lease prevents two workers sending the same item concurrently.
            delivery.available_at = timezone.now() + timedelta(minutes=5)
            delivery.attempts += 1
            delivery.save(update_fields=["available_at", "attempts"])
        subscription = PushSubscription.objects.select_related("user").filter(pk=delivery.subscription_id).first()
        if not subscription:
            continue
        allowed = subscription.user.is_active
        if delivery.kind != "test":
            obj, permission = event_object(delivery.kind, delivery.object_id)
            allowed = (
                allowed
                and getattr(subscription, delivery.kind)
                and obj is not None
                and can_read(subscription.user, obj, permission)
            )
        if not allowed or delivery.created_at < timezone.now() - timedelta(days=1):
            delivery.delete()
            continue
        payload = {
            "title": "JF-Manager",
            "body": {
                "services": "Ein Dienst wurde angelegt oder geändert. Details findest du im Dienstbuch.",
                "orders": "Es gibt Neuigkeiten zu einer Bestellung.",
                "test": "Push-Mitteilungen sind auf diesem Gerät eingerichtet.",
            }[delivery.kind],
            "url": {"services": "/servicebook", "orders": "/orders", "test": "/profile"}[delivery.kind],
            "tag": f"jf-{delivery.kind}-{delivery.object_id}",
        }
        try:
            validate_endpoint(subscription.endpoint)
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=json.dumps(payload),
                vapid_private_key=config["private_key"],
                vapid_claims={"sub": config["subject"]},
                ttl=3600,
                timeout=10,
            )
        except WebPushException as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in (404, 410):
                subscription.delete()
            elif delivery.attempts >= 5:
                delivery.delete()
                logger.warning("Push delivery %s abandoned after five attempts (status %s)", delivery_id, status)
            else:
                delivery.available_at = timezone.now() + timedelta(minutes=2**delivery.attempts)
                delivery.save(update_fields=["available_at"])
        except Exception:
            # Do not log endpoint/key material from provider exceptions.
            logger.warning("Push delivery %s failed", delivery_id)
            if delivery.attempts >= 5:
                delivery.delete()
        else:
            delivery.delete()
            processed += 1
    return processed
