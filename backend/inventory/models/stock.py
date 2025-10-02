from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction as db_transaction
from .item import Item
from .variant import ItemVariant
from .location import StorageLocation


class Stock(models.Model):
    """Bestand eines Artikels/Variante an einem Lagerort"""
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Artikel'
    )
    item_variant = models.ForeignKey(
        ItemVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Artikel-Variante'
    )
    location = models.ForeignKey(StorageLocation, on_delete=models.CASCADE, verbose_name='Lagerort')
    quantity = models.PositiveIntegerField(default=0, verbose_name='Menge')

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(item__isnull=False, item_variant__isnull=True) |
                      models.Q(item__isnull=True, item_variant__isnull=False),
                name='stock_either_item_or_variant'
            )
        ]
        verbose_name = 'Bestand'
        verbose_name_plural = 'Bestände'

    def clean(self):
        if not self.item and not self.item_variant:
            raise ValidationError('Entweder Artikel oder Artikel-Variante muss ausgewählt werden.')
        if self.item and self.item_variant:
            raise ValidationError('Nur eines von Artikel oder Artikel-Variante kann ausgewählt werden.')

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
        ('IN', 'Eingang'),
        ('OUT', 'Ausgang'),
        ('MOVE', 'Umlagerung'),
        ('LOAN', 'Ausleihe'),
        ('RETURN', 'Rückgabe'),
        ('DISCARD', 'Aussortierung'),
    ]
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name='Transaktionstyp')
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Artikel'
    )
    item_variant = models.ForeignKey(
        ItemVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Artikel-Variante'
    )
    source = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='outgoing_transactions',
        verbose_name='Quelle'
    )
    target = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='incoming_transactions',
        verbose_name='Ziel'
    )
    quantity = models.PositiveIntegerField(verbose_name='Menge')
    date = models.DateTimeField(auto_now_add=True, verbose_name='Datum')
    note = models.TextField(blank=True, verbose_name='Notiz')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Benutzer'
    )

    class Meta:
        verbose_name = 'Transaktion'
        verbose_name_plural = 'Transaktionen'
        ordering = ['-date']
        permissions = [
            ('discard_items', 'Can discard items'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(item__isnull=False, item_variant__isnull=True) |
                      models.Q(item__isnull=True, item_variant__isnull=False),
                name='transaction_either_item_or_variant'
            )
        ]

    def clean(self):
        if not self.item and not self.item_variant:
            raise ValidationError('Entweder Artikel oder Artikel-Variante muss ausgewählt werden.')
        if self.item and self.item_variant:
            raise ValidationError('Nur eines von Artikel oder Artikel-Variante kann ausgewählt werden.')
        if self.transaction_type in ['IN', 'RETURN'] and not self.target:
            raise ValidationError('Ziel ist erforderlich für Eingang/Rückgabe.')
        if self.transaction_type in ['OUT', 'DISCARD'] and not self.source:
            raise ValidationError('Quelle ist erforderlich für Ausgang/Aussortierung.')
        if self.transaction_type in ['MOVE', 'LOAN'] and (not self.source or not self.target):
            raise ValidationError('Quelle und Ziel sind erforderlich für Umlagerung/Ausleihe.')
        if self.source == self.target and self.source is not None:
            raise ValidationError('Quelle und Ziel dürfen nicht identisch sein.')

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
        self.clean()
        with db_transaction.atomic():
            super().save(*args, **kwargs)
            self.update_stock()

    def update_stock(self):
        stock_params = {}
        if self.item:
            stock_params = {'item': self.item, 'item_variant': None}
        elif self.item_variant:
            stock_params = {'item': None, 'item_variant': self.item_variant}
        if self.transaction_type in ['IN', 'RETURN']:
            stock, created = Stock.objects.get_or_create(
                location=self.target,
                defaults={'quantity': 0, **stock_params},
                **stock_params
            )
            stock.quantity += self.quantity
            stock.save()
        elif self.transaction_type in ['OUT', 'DISCARD']:
            try:
                stock = Stock.objects.get(location=self.source, **stock_params)
                if stock.quantity < self.quantity:
                    raise ValidationError(f'Nicht genügend Bestand. Verfügbar: {stock.quantity}')
                stock.quantity -= self.quantity
                stock.save()
            except Stock.DoesNotExist:
                raise ValidationError('Kein Bestand am Quellort vorhanden.')
        elif self.transaction_type in ['MOVE', 'LOAN']:
            try:
                source_stock = Stock.objects.get(location=self.source, **stock_params)
                if source_stock.quantity < self.quantity:
                    raise ValidationError(f'Nicht genügend Bestand. Verfügbar: {source_stock.quantity}')
                source_stock.quantity -= self.quantity
                source_stock.save()
            except Stock.DoesNotExist:
                raise ValidationError('Kein Bestand am Quellort vorhanden.')
            target_stock, created = Stock.objects.get_or_create(
                location=self.target,
                defaults={'quantity': 0, **stock_params},
                **stock_params
            )
            target_stock.quantity += self.quantity
            target_stock.save()
