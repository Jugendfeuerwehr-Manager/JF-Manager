"""UX-10.1: give active staff superusers the existing open team tasks and recent team notices."""

from datetime import timedelta

from django.conf import settings
from django.db import migrations
from django.db.models import Q
from django.utils import timezone


def backfill(apps, schema_editor, now=None):
    user_model = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    item_model = apps.get_model("notifications", "InboxItem")
    recipient_model = apps.get_model("notifications", "InboxRecipient")
    superusers = list(
        user_model.objects.filter(is_superuser=True, is_active=True, account_kind="staff").values_list("pk", flat=True)
    )
    if not superusers:
        return 0
    cutoff = (now or timezone.now()) - timedelta(days=30)
    items = item_model.objects.exclude(permission="").filter(
        Q(item_type="task", task_state="open") | Q(item_type="notice", updated_at__gte=cutoff)
    )
    created = 0
    for item_id in items.values_list("pk", flat=True):
        existing = set(recipient_model.objects.filter(item_id=item_id).values_list("user_id", flat=True))
        rows = [recipient_model(item_id=item_id, user_id=uid) for uid in superusers if uid not in existing]
        recipient_model.objects.bulk_create(rows)
        created += len(rows)
    return created


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0003_delivery"),
        ("users", "0013_account_kind"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
