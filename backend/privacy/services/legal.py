"""Editing and publishing the legal texts."""

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from jf_manager_backend.html_safety import sanitize_rich_html
from privacy.models import LegalPage, LegalPageVersion

DEFAULT_TITLES = {LegalPage.Kind.IMPRINT: "Impressum", LegalPage.Kind.PRIVACY: "Datenschutzerklärung"}


class LegalPageError(Exception):
    pass


def get_page(kind):
    page, _ = LegalPage.objects.get_or_create(kind=kind, defaults={"draft_title": DEFAULT_TITLES[kind]})
    return page


def ensure_pages():
    return [get_page(kind) for kind in LegalPage.Kind.values]


def save_draft(page, *, title, body, user):
    page.draft_title = title
    page.draft_body = sanitize_rich_html(body)
    page.updated_by = user
    page.save(update_fields=["draft_title", "draft_body", "updated_by", "updated_at"])
    return page


def publish(page, *, user, change_note=""):
    """Freeze the current draft as the next version."""
    title = page.draft_title.strip()
    body = sanitize_rich_html(page.draft_body)
    if not title or not body.strip():
        raise LegalPageError("Titel und Text dürfen zum Veröffentlichen nicht leer sein.")
    with transaction.atomic():
        LegalPage.objects.select_for_update().get(pk=page.pk)
        last = page.versions.aggregate(last=Max("version"))["last"] or 0
        current = page.versions.filter(version=last).first()
        if current and current.title == title and current.body == body:
            raise LegalPageError("Der Entwurf entspricht der veröffentlichten Version.")
        return LegalPageVersion.objects.create(
            page=page,
            version=last + 1,
            title=title,
            body=body,
            change_note=change_note,
            published_at=timezone.now(),
            published_by=user,
        )


def published(kind):
    """The current published version of a kind, or None."""
    return LegalPageVersion.objects.filter(page__kind=kind).order_by("-version").first()


def version_label(kind):
    """Reference stored with a consent, e.g. ``privacy:v3``; empty if nothing is published."""
    current = published(kind)
    return f"{kind}:v{current.version}" if current else ""
