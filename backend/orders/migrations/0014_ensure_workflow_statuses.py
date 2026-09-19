from django.db import migrations


def ensure_workflow_statuses(apps, schema_editor):
    OrderStatus = apps.get_model("orders", "OrderStatus")
    defaults = [
        ("ORDERED", "Bestellt", "#f59e0b", 10),
        ("RECEIVED", "Eingegangen", "#0ea5e9", 20),
        ("DELIVERED", "Ausgegeben", "#22c55e", 30),
        ("CANCELLED", "Storniert", "#ef4444", 40),
    ]
    for code, name, color, sort_order in defaults:
        OrderStatus.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "color": color,
                "sort_order": sort_order,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("orders", "0013_orderitem_receipt_transaction")]

    operations = [migrations.RunPython(ensure_workflow_statuses, migrations.RunPython.noop)]
