# Inventory System

## Overview

A Django-based inventory and stock management system for the youth fire brigade. Manages articles, storage locations, stock levels, and transactions.

## Features

- **Article management** with categories and variable attributes (JSON schema)
- **Storage locations** including member assignments
- **Real-time stock tracking** with automatic updates
- **Transaction management** with 6 transaction types
- **Permission-based access** (Admin, Jugendleiter, Mitglied)
- **Discard tracking** with reason codes and statistics

## Data Model

### Category
- `name` – Category name
- `schema` – JSON schema for variable attributes

### Item
- `name` – Article name
- `category` – Associated category
- `base_unit` – Base unit (Stück, Liter, etc.)
- `attributes` – JSON attributes (size, color, etc.)

### StorageLocation
- `name` – Location name
- `is_member` – Whether it's a member-assigned location
- `member` – Linked member (optional)

### Stock
- `item` – Article
- `location` – Storage location
- `quantity` – Quantity (automatically managed via transactions)

### Transaction
- `transaction_type` – IN, OUT, LOAN, RETURN, MOVE, DISCARD
- `item`, `source`, `target`, `quantity`, `user`, `note`
- `discard_reason` – Required for DISCARD transactions (see below)

## Transaction Types

| Type | Description |
|------|-------------|
| `IN` | Incoming goods |
| `OUT` | Outgoing goods |
| `LOAN` | Loan to member |
| `RETURN` | Return from member |
| `MOVE` | Transfer between locations |
| `DISCARD` | Discard defective/old items |

**Important**: All stock changes must go through transactions, never modify Stock directly.

```python
# ✅ Correct
Transaction.objects.create(
    transaction_type='IN', item=item, target=location,
    quantity=10, user=request.user
)

# ❌ Wrong
Stock.objects.create(item=item, location=location, quantity=10)
```

## Permissions

| Role | Access |
|------|--------|
| Admin | Full access, including DISCARD and delete |
| Jugendleiter | Manage items, create transactions (except DISCARD) |
| Mitglied | View own loans only |

### Django Permissions
- `inventory.view_item`, `inventory.add_item`, `inventory.change_item`, `inventory.delete_item`
- `inventory.view_stock`, `inventory.view_transaction`, `inventory.add_transaction`
- `inventory.discard_items` – Discard items (admin only)

## Discard Tracking

DISCARD transactions require a `discard_reason`:

| Code | Label |
|------|-------|
| `LOST` | Verloren (Lost) |
| `DAMAGED` | Beschädigt (Damaged) |
| `WORN_OUT` | Verschlissen (Worn out) |
| `STOLEN` | Gestohlen (Stolen) |
| `OTHER` | Sonstiges (Other) |

Validation rules:
- DISCARD transactions **must** have a `discard_reason`
- Non-DISCARD transactions **cannot** have a `discard_reason`

### Discard Statistics Endpoint

```
GET /api/v1/inventory/transactions/discard-statistics/
```

Returns comprehensive statistics about discarded items including counts by reason, item, and time period.

## API Endpoints

See [API Reference](../api/reference.md#inventory) for the full endpoint list.

## Setup

```bash
pipenv run python manage.py migrate inventory

# Optional: create sample data
pipenv run python manage.py create_inventory_sample_data
pipenv run python manage.py create_inventory_sample_data --clear  # Reset
```
