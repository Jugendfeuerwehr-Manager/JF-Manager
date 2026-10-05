from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction as db_transaction
from django.db.models import F
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .item import Item
from .location import StorageLocation
from .variant import ItemVariant

LEDGER_ONLY = "Bestände ändern sich nur durch Buchungen (Eingang, Ausgabe, Rückgabe, Umlagerung, Aussortierung)."
IMMUTABLE = "Gebuchte Bestandsbewegungen sind unveränderlich. Bitte eine Gegenbuchung anlegen."


class StockQuerySet(models.QuerySet):
    """Quantities move only through ``Transaction.update_stock``."""

    def update(self, **kwargs):
        raise ValidationError(LEDGER_ONLY)

    def _apply_booking(self, delta):
        # Single entry point for quantity changes, used by the booking service.
        return super().update(quantity=F("quantity") + delta)

    def delete(self):
        if self.filter(quantity__gt=0).exists():
            raise ValidationError("Bestände mit Menge können nicht gelöscht werden. " + LEDGER_ONLY)
        return super().delete()


class TransactionQuerySet(models.QuerySet):
    """Booked movements cannot be changed or deleted in bulk either."""

    def update(self, **kwargs):
        raise ValidationError(IMMUTABLE)

    def delete(self):
        raise ValidationError("Gebuchte Bestandsbewegungen dürfen nicht gelöscht werden.")

    def clear_former_member_names(self):
        """Privacy action: the only permitted change to booked movements."""
        return super(TransactionQuerySet, self.exclude(former_member_name="")).update(former_member_name="")


class Stock(models.Model):
    """Bestand eines Artikels/Variante an einem Lagerort"""

    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Artikel")
    item_variant = models.ForeignKey(
        ItemVariant, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Artikel-Variante"
    )
    location = models.ForeignKey(StorageLocation, on_delete=models.CASCADE, verbose_name="Lagerort")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Menge")

    objects = StockQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(item__isnull=False, item_variant__isnull=True)
                | models.Q(item__isnull=True, item_variant__isnull=False),
                name="stock_either_item_or_variant",
            ),
            models.UniqueConstraint(
                fields=["location", "item"], condition=models.Q(item__isnull=False), name="stock_unique_item_location"
            ),
            models.UniqueConstraint(
                fields=["location", "item_variant"],
                condition=models.Q(item_variant__isnull=False),
                name="stock_unique_variant_location",
            ),
            models.CheckConstraint(check=models.Q(quantity__gte=0), name="stock_nonnegative_quantity"),
        ]
        verbose_name = "Bestand"
        verbose_name_plural = "Bestände"

    def clean(self):
        if not self.item and not self.item_variant:
            raise ValidationError("Entweder Artikel oder Artikel-Variante muss ausgewählt werden.")
        if self.item and self.item_variant:
            raise ValidationError("Nur eines von Artikel oder Artikel-Variante kann ausgewählt werden.")

    def save(self, *args, **kwargs):
        # New rows start empty; quantities change only via bookings.
        if self.pk is None:
            if self.quantity:
                raise ValidationError(LEDGER_ONLY)
        elif type(self).objects.filter(pk=self.pk).exclude(quantity=self.quantity).exists():
            raise ValidationError(LEDGER_ONLY)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if type(self).objects.filter(pk=self.pk, quantity__gt=0).exists():
            raise ValidationError("Bestände mit Menge können nicht gelöscht werden. " + LEDGER_ONLY)
        return super().delete(*args, **kwargs)

    def __str__(self):
        item_name = self.get_item_name()
        return f"{item_name} @ {self.location.name}: {self.quantity}"

    def get_item_name(self):
        if self.item:
            return self.item.name
        elif self.item_variant:
            return str(self.item_variant)
        return "Unbekannter Artikel"

    def get_item_object(self):
        return self.item or self.item_variant

    def get_category(self):
        if self.item:
            return self.item.category
        elif self.item_variant:
            return self.item_variant.parent_item.category
        return None


class Transaction(models.Model):
    """Transaktion für Bestandsänderungen"""

    TRANSACTION_TYPES = [
        ("IN", "Eingang"),
        ("OUT", "Ausgang"),
        ("MOVE", "Umlagerung"),
        ("LOAN", "Ausleihe"),
        ("RETURN", "Rückgabe"),
        ("DISCARD", "Aussortierung"),
    ]
    DISCARD_REASONS = [
        ("LOST", "Verloren"),
        ("DAMAGED", "Beschädigt"),
        ("WORN_OUT", "Verschlissen"),
        ("STOLEN", "Gestohlen"),
        ("OTHER", "Sonstiges"),
    ]
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name="Transaktionstyp")
    discard_reason = models.CharField(
        max_length=20,
        choices=DISCARD_REASONS,
        blank=True,
        null=True,
        verbose_name="Aussortierungsgrund",
        help_text="Grund für die Aussortierung (nur bei DISCARD-Transaktionen)",
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Artikel")
    item_variant = models.ForeignKey(
        ItemVariant, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Artikel-Variante"
    )
    source = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outgoing_transactions",
        verbose_name="Quelle",
    )
    target = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incoming_transactions",
        verbose_name="Ziel",
    )
    quantity = models.PositiveIntegerField(verbose_name="Menge")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Datum")
    note = models.TextField(blank=True, verbose_name="Notiz")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Benutzer"
    )
    reverses = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversal",
        verbose_name="Korrigiert Buchung",
    )

    former_member_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Ehemaliges Mitglied",
        help_text="Name des Mitglieds, das zum Zeitpunkt der Transaktion verknüpft war (wird gesetzt, wenn ein Mitglied gelöscht wird)",
    )

    objects = TransactionQuerySet.as_manager()

    class Meta:
        verbose_name = "Transaktion"
        verbose_name_plural = "Transaktionen"
        ordering = ["-date"]
        permissions = [
            ("discard_items", "Can discard items"),
            ("clear_former_member_names", "Can clear former member names from transactions"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(item__isnull=False, item_variant__isnull=True)
                | models.Q(item__isnull=True, item_variant__isnull=False),
                name="transaction_either_item_or_variant",
            )
        ]

    def clean(self):
        if not self.item and not self.item_variant:
            raise ValidationError("Entweder Artikel oder Artikel-Variante muss ausgewählt werden.")
        if self.item and self.item_variant:
            raise ValidationError("Nur eines von Artikel oder Artikel-Variante kann ausgewählt werden.")
        if self.transaction_type == "IN" and not self.target:
            raise ValidationError("Ziel ist erforderlich für Eingang.")
        if self.transaction_type == "RETURN" and (not self.source or not self.target):
            raise ValidationError("Quelle und Ziel sind erforderlich für Rückgabe.")
        if self.transaction_type in ["OUT", "DISCARD"] and not self.source:
            raise ValidationError("Quelle ist erforderlich für Ausgang/Aussortierung.")
        if self.transaction_type in ["MOVE", "LOAN"] and (not self.source or not self.target):
            raise ValidationError("Quelle und Ziel sind erforderlich für Umlagerung/Ausleihe.")
        if self.source == self.target and self.source is not None:
            raise ValidationError("Quelle und Ziel dürfen nicht identisch sein.")
        # Validate discard_reason is only set for DISCARD transactions
        if self.transaction_type == "DISCARD" and not self.discard_reason:
            raise ValidationError("Aussortierungsgrund ist erforderlich für DISCARD-Transaktionen.")
        if self.transaction_type != "DISCARD" and self.discard_reason:
            raise ValidationError("Aussortierungsgrund kann nur bei DISCARD-Transaktionen angegeben werden.")

    def __str__(self):
        item_name = self.get_item_name()
        return f"{self.get_transaction_type_display()}: {item_name} ({self.quantity})"

    def get_item_name(self):
        if self.item:
            return self.item.name
        elif self.item_variant:
            return str(self.item_variant)
        return "Unbekannter Artikel"

    def get_item_object(self):
        return self.item or self.item_variant

    def save(self, *args, **kwargs):
        if self.pk is not None:
            previous = type(self).objects.get(pk=self.pk)
            immutable_fields = (
                "transaction_type",
                "discard_reason",
                "item_id",
                "item_variant_id",
                "source_id",
                "target_id",
                "quantity",
                "date",
                "note",
                "user_id",
                "former_member_name",
                "reverses_id",
            )
            if any(getattr(self, field) != getattr(previous, field) for field in immutable_fields):
                raise ValidationError(IMMUTABLE)
            return
        self.clean()
        with db_transaction.atomic():
            super().save(*args, **kwargs)
            self.update_stock()

    def delete(self, *args, **kwargs):
        raise ValidationError("Gebuchte Bestandsbewegungen dürfen nicht gelöscht werden.")

    def update_stock(self):
        stock_params = {"item_id": self.item_id, "item_variant_id": self.item_variant_id}
        target_stock = None
        if self.transaction_type in ("IN", "MOVE", "LOAN", "RETURN"):
            target_stock, _created = Stock.objects.get_or_create(
                location=self.target, defaults={"quantity": 0}, **stock_params
            )

        source_stock = None
        if self.transaction_type != "IN":
            source_stock = Stock.objects.filter(location=self.source, **stock_params).first()
            if source_stock is None:
                raise ValidationError("Kein Bestand am Quellort vorhanden.")

        # Lock existing rows in one stable order, including the target of a transfer.
        stock_ids = [stock.pk for stock in (source_stock, target_stock) if stock is not None]
        list(Stock.objects.select_for_update().filter(pk__in=stock_ids).order_by("pk"))

        if source_stock is not None:
            changed = Stock.objects.filter(pk=source_stock.pk, quantity__gte=self.quantity)._apply_booking(
                -self.quantity
            )
            if not changed:
                current = Stock.objects.get(pk=source_stock.pk).quantity
                raise ValidationError(f"Nicht genügend Bestand. Verfügbar: {current}")
        if target_stock is not None:
            Stock.objects.filter(pk=target_stock.pk)._apply_booking(self.quantity)


@receiver(pre_delete, sender=Transaction)
def protect_booked_movement(sender, instance, **kwargs):
    # Also covers deletions collected by cascades from related objects.
    raise ValidationError("Gebuchte Bestandsbewegungen dürfen nicht gelöscht werden.")


@receiver(pre_delete, sender=Stock)
def protect_stock_with_quantity(sender, instance, **kwargs):
    if Stock.objects.filter(pk=instance.pk, quantity__gt=0).exists():
        raise ValidationError("Bestände mit Menge können nicht gelöscht werden. " + LEDGER_ONLY)
