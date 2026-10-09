"""Delivery of notifications by e-mail and push (NOTIF-01.5).

Producers create inbox entries (``notifications.inbox.notify``) and call
``queue_email``/``queue_push`` here. E-mails go through a durable outbox
(``EmailDelivery``), idempotent per event key, rendered at send time with the
current template and sent by the notification worker (``send_push --loop``).
E-mail and push are on by default (E8, E16, E19; off for superusers, UX-10.1) and can be switched off per
account and kind; the inbox cannot.
"""

import logging
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .emails import ensure_flat, render
from .models import EmailDelivery, NotificationPreference, PushDelivery, PushSubscription

logger = logging.getLogger("security.notifications")

# Kinds an account can configure, by audience (labels for the profile page).
PORTAL_KINDS = {
    "session_published": "Neue Dienste",
    "session_changed": "Geänderte oder abgesagte Dienste",
    "waitlist_placed": "Platz auf der Warteliste",
    "waitlist_promoted": "Nachgerückt",
    "assign_published": "Zuteilung",
    "cr_decided": "Entscheidung über Änderungsanträge",
    "parent_access_end": "Ende des Elternzugangs",
}
STAFF_KINDS = {
    "cr_submitted": "Neue Änderungsanträge",
    "reg_cancelled": "Kurzfristige Abmeldungen",
    "reg_digest": "Tageszusammenfassung der Meldungen",
    "slot_free_manual": "Platz frei (Warteliste manuell)",
    "staffing_at_risk": "Mindestbesetzung gefährdet",
    "eligibility_conflict": "Voraussetzung nicht mehr erfüllt",
    "parent_access_end": "Ende von Elternzugängen",
    "account_link": "Kontoverknüpfungen",
}


def kinds_for(user):
    return PORTAL_KINDS if user.is_portal_account else STAFF_KINDS


def default_channel(user, explicit=True):
    """Default without a saved preference: on, except for implicitly addressed staff superusers (UX-10.1).

    Superusers see every team entry in the inbox; mail and push for entries they
    only receive because they are superuser would flood them, so for accounts
    without any role those stay opt-in per kind in the profile. ``explicit`` marks recipients chosen by
    responsibility (e.g. session lead), who keep the default.
    """
    if explicit or not user.is_superuser or user.is_portal_account:
        return True
    # A superuser who also holds a real role (department role or group) keeps the
    # normal default; only pure administration accounts stay quiet.
    return user.department_roles.exists() or user.groups.exists()


def wants(user, kind, channel, explicit=True):
    pref = NotificationPreference.objects.filter(user=user, kind=kind).first()
    return getattr(pref, channel) if pref else default_channel(user, explicit)


def _frontend(path):
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}"


def common_context(user, *, open_url, withdraw_url="", withdraw_label="", actions=()):
    """Shared, flat variables of every notification mail (concept 4.9.3 item 6)."""
    from dynamic_preferences.registries import global_preferences_registry

    prefs = global_preferences_registry.manager()
    portal = user.is_portal_account
    link = getattr(user, "account_link", None) if portal else None
    kind = "staff" if not portal else ("parent" if link and link.parent_id else "member")
    return {
        "org": {"name": prefs["general__title"], "color": str(prefs["general__brand_color"] or "")},
        "recipient": {"first_name": user.first_name or user.username, "kind": kind},
        "links": {
            "open": open_url,
            "preferences": _frontend("/portal/profil#mitteilungen" if portal else "/profile#mitteilungen"),
            "withdraw": withdraw_url,
            "withdraw_label": withdraw_label,
            "inbox": "" if portal else _frontend("/eingang"),
        },
        "actions": list(actions),
        "sent_at": timezone.localtime().strftime("%d.%m.%Y, %H:%M Uhr"),
        "site_name": prefs["general__title"],
    }


def queue_email(kind, user, context, *, event_key, bundle_key="", delay=timedelta(0), explicit=False):
    """Queue one mail and return it; the same event key never yields a second mail (then None)."""
    if not user.is_active or not user.email or not wants(user, kind, "email", explicit):
        return None
    ensure_flat(context)
    delivery, created = EmailDelivery.objects.get_or_create(
        event_key=event_key[:160],
        defaults={
            "user": user,
            "kind": kind,
            "context": context,
            "bundle_key": bundle_key[:160],
            "send_after": timezone.now() + delay,
        },
    )
    return delivery if created else None  # None: already queued for this event


def queue_push(user, item, category, explicit=False):
    """Push for an inbox entry; the lock screen shows no names (4.9.1)."""
    from settings_manager.push_configuration import effective_push

    if item is None or not effective_push()["enabled"] or not wants(user, item.kind, "push", explicit):
        return
    for subscription in PushSubscription.objects.filter(user=user, **{category: True}):
        PushDelivery.objects.get_or_create(subscription=subscription, kind=category, object_id=item.pk)


# ----------------------------------------------------------------------------- bundling
def _merge_session_published(contexts):
    """Several published dates of one series in one mail (E19)."""
    first = dict(contexts[0])
    dates = [c["session"]["date"] for c in contexts]
    first["series"] = {"title": first["session"]["title"], "dates": dates}
    return first


MERGERS = {"session_published": _merge_session_published}


# ----------------------------------------------------------------------------- worker
def _send(delivery_user, kind, context):
    subject, html, text = render(kind, context)
    send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, [delivery_user.email], html_message=html)


def deliver_emails(limit=50, now=None):
    """Send due outbox entries; failed sends back off and are dropped after five attempts."""
    now = now or timezone.now()
    sent = 0
    for delivery_id in list(
        EmailDelivery.objects.filter(send_after__lte=now).order_by("pk").values_list("pk", flat=True)[:limit]
    ):
        with transaction.atomic():
            delivery = EmailDelivery.objects.select_for_update().filter(pk=delivery_id, send_after__lte=now).first()
            if delivery is None:
                continue
            group = [delivery]
            if delivery.bundle_key:
                group = list(
                    EmailDelivery.objects.select_for_update()
                    .filter(user_id=delivery.user_id, bundle_key=delivery.bundle_key, send_after__lte=now)
                    .order_by("pk")
                )
            ids = [d.pk for d in group]
            EmailDelivery.objects.filter(pk__in=ids).update(send_after=now + timedelta(minutes=5))
        user = delivery.user
        if not user.is_active or not user.email:
            EmailDelivery.objects.filter(pk__in=ids).delete()
            continue
        contexts = [d.context for d in group]
        context = MERGERS[delivery.kind](contexts) if len(contexts) > 1 and delivery.kind in MERGERS else contexts[0]
        try:
            _send(user, delivery.kind, context)
        except (ImproperlyConfigured, OSError, SMTPException) as exc:
            attempts = delivery.attempts + 1
            if attempts >= 5:
                EmailDelivery.objects.filter(pk__in=ids).delete()
                logger.warning(
                    "notification mail dropped after five attempts",
                    extra={"kind": delivery.kind, "error": type(exc).__name__},
                )
            else:
                EmailDelivery.objects.filter(pk__in=ids).update(
                    attempts=attempts, send_after=now + timedelta(minutes=2**attempts)
                )
            continue
        EmailDelivery.objects.filter(pk__in=ids).delete()
        sent += 1
    return sent
