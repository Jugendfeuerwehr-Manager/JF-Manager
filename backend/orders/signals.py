"""Module-level signal receivers keep a real reference; Django's default weak-ref
connect() would otherwise garbage-collect closures defined inside AppConfig.ready().
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from inventory.models import Item, ItemVariant

from .services.inventory_sync import sync_orderable_item


@receiver(post_save, sender=Item, dispatch_uid="orders_sync_orderable_item_on_item_save")
def sync_orderable_item_on_item_save(sender, instance, **kwargs):
    sync_orderable_item(instance)


@receiver(post_save, sender=ItemVariant, dispatch_uid="orders_sync_orderable_item_on_variant_save")
def sync_orderable_item_on_variant_save(sender, instance, **kwargs):
    sync_orderable_item(instance.parent_item)


@receiver(post_delete, sender=ItemVariant, dispatch_uid="orders_sync_orderable_item_on_variant_delete")
def sync_orderable_item_on_variant_delete(sender, instance, **kwargs):
    sync_orderable_item(instance.parent_item)
