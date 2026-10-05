"""Database guard for booked movements (SEC-09.5b).

On PostgreSQL a trigger rejects DELETE and any UPDATE of a booked movement
except clearing ``former_member_name`` (privacy action). This also stops raw
SQL and future code paths that bypass the ORM guards. Other databases rely on
the model and queryset guards. Data repairs must disable the trigger
explicitly inside a maintenance window.
"""

from django.db import migrations

FORWARD = """
CREATE OR REPLACE FUNCTION inventory_transaction_immutable() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Gebuchte Bestandsbewegungen duerfen nicht geloescht werden.'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (to_jsonb(NEW) - 'former_member_name') IS DISTINCT FROM (to_jsonb(OLD) - 'former_member_name')
       OR (NEW.former_member_name <> '' AND NEW.former_member_name IS DISTINCT FROM OLD.former_member_name) THEN
        RAISE EXCEPTION 'Gebuchte Bestandsbewegungen sind unveraenderlich.'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER inventory_transaction_immutable
    BEFORE UPDATE OR DELETE ON inventory_transaction
    FOR EACH ROW EXECUTE FUNCTION inventory_transaction_immutable();
"""

BACKWARD = """
DROP TRIGGER IF EXISTS inventory_transaction_immutable ON inventory_transaction;
DROP FUNCTION IF EXISTS inventory_transaction_immutable();
"""


def forward(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(FORWARD)


def backward(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(BACKWARD)


class Migration(migrations.Migration):
    dependencies = [("inventory", "0015_stockbookingrequest_and_more")]

    operations = [migrations.RunPython(forward, backward)]
