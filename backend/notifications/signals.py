from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .services import enqueue_event


@receiver(pre_save, sender="servicebook.Service")
def remember_service(sender, instance, raw=False, **kwargs):
    if raw:
        return
    fields = ("start", "end", "place", "topic", "description", "events", "department_id")
    old = sender.objects.filter(pk=instance.pk).values(*fields).first() if instance.pk else None
    instance._push_changed = old is None or any(old[field] != getattr(instance, field) for field in fields)


@receiver(post_save, sender="servicebook.Service")
def service_changed(sender, instance, raw=False, **kwargs):
    if not raw and getattr(instance, "_push_changed", False):
        transaction.on_commit(lambda pk=instance.pk: enqueue_event("services", pk))


@receiver(post_save, sender="orders.Order")
def order_created(sender, instance, created=False, raw=False, **kwargs):
    if created and not raw:
        transaction.on_commit(lambda pk=instance.pk: enqueue_event("orders", pk))


@receiver(post_save, sender="orders.OrderItemStatusHistory")
def order_status_changed(sender, instance, created=False, raw=False, **kwargs):
    if created and not raw:
        transaction.on_commit(lambda pk=instance.order_item.order_id: enqueue_event("orders", pk))
