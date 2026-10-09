from django.conf import settings
from django.db import models
from django.utils import timezone


class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    endpoint = models.URLField(max_length=2048, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    services = models.BooleanField(default=True)
    orders = models.BooleanField(default=True)
    # NOTIF-01.5: change requests (staff) and participation (staff and portal accounts).
    requests = models.BooleanField(default=True)
    participation = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PushDelivery(models.Model):
    subscription = models.ForeignKey(PushSubscription, on_delete=models.CASCADE)
    kind = models.CharField(max_length=16)
    object_id = models.PositiveBigIntegerField()
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["subscription", "kind", "object_id"], name="unique_device_push_event")
        ]


class InboxItem(models.Model):
    """One entry for the team (NOTIF-01, E15): a task with a team status or a notice.

    Titles are short and contain no free text from requests or cancellation notes.
    ``permission`` and ``department`` are re-checked whenever a recipient reads the inbox,
    so withdrawn rights hide the entry again.
    """

    class Category(models.TextChoices):
        REQUESTS = "requests", "Anträge"
        REGISTRATIONS = "registrations", "Meldungen"
        STAFFING = "staffing", "Besetzung"
        ACCOUNTS = "accounts", "Konten"
        PARTICIPATION = "participation", "Teilnahme"  # portal notices

    class ItemType(models.TextChoices):
        TASK = "task", "Aufgabe"
        NOTICE = "notice", "Hinweis"

    class TaskState(models.TextChoices):
        OPEN = "open", "Offen"
        DONE = "done", "Erledigt"

    kind = models.CharField(max_length=30)
    category = models.CharField(max_length=20, choices=Category.choices)
    item_type = models.CharField(max_length=10, choices=ItemType.choices)
    department = models.ForeignKey("departments.Department", null=True, blank=True, on_delete=models.CASCADE)
    object_type = models.CharField(max_length=40, blank=True, default="")
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    title = models.CharField(max_length=200)
    link = models.CharField(max_length=300, blank=True, default="")
    permission = models.CharField(max_length=100, blank=True, default="")
    count = models.PositiveIntegerField(default=1)
    group_key = models.CharField(max_length=120, null=True, blank=True)
    task_state = models.CharField(max_length=10, choices=TaskState.choices, blank=True, default="")
    done_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    done_at = models.DateTimeField(null=True, blank=True)
    done_via = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "Eingangseintrag"
        verbose_name_plural = "Eingangseinträge"
        ordering = ["-updated_at", "-pk"]
        constraints = [
            # One live bundle per key: new events update it instead of piling up (4.9.2).
            models.UniqueConstraint(
                fields=["group_key"], condition=models.Q(group_key__isnull=False), name="unique_inbox_group_key"
            ),
        ]
        indexes = [models.Index(fields=["object_type", "object_id"])]

    def __str__(self):
        return self.title


class InboxRecipient(models.Model):
    item = models.ForeignKey(InboxItem, on_delete=models.CASCADE, related_name="recipients")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inbox_entries")
    read_at = models.DateTimeField(null=True, blank=True)
    hidden_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["item", "user"], name="unique_inbox_recipient")]


class NotificationPreference(models.Model):
    """Per account and kind: e-mail and push can be switched off; the inbox cannot (E8)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="channel_preferences")
    kind = models.CharField(max_length=30)
    email = models.BooleanField(default=True)
    push = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "kind"], name="unique_notification_preference")]


class EmailDelivery(models.Model):
    """Durable e-mail outbox (NOTIF-01.5): idempotent per event key, rendered at send time.

    ``bundle_key`` groups deliveries that become one mail (e.g. a published series);
    they wait until ``send_after`` so that the whole batch is known.
    """

    event_key = models.CharField(max_length=160, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=30)
    context = models.JSONField(default=dict)
    bundle_key = models.CharField(max_length=160, blank=True, default="", db_index=True)
    send_after = models.DateTimeField(default=timezone.now, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
