"""Opening balances are ordinary incoming bookings, so the ledger stays complete."""

from .models import Stock, Transaction


def book_opening_stock(location, quantity, *, item=None, item_variant=None, user=None, note="Anfangsbestand"):
    """Book ``quantity`` into ``location`` and return the resulting stock row."""
    Transaction.objects.create(
        transaction_type="IN",
        item=item,
        item_variant=item_variant,
        target=location,
        quantity=quantity,
        user=user,
        note=note,
    )
    return Stock.objects.get(location=location, item=item, item_variant=item_variant)
