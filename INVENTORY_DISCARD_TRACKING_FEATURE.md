# Inventory Discard Tracking Feature

## Overview

This feature adds comprehensive tracking and reporting for trashed/lost inventory items. Previously, the system had a basic `DISCARD` transaction type but lacked the ability to specify **why** items were discarded and proper reporting capabilities.

## What Changed

### Backend Changes

#### 1. Database Model (`backend/inventory/models/stock.py`)

**New Field Added:**
```python
discard_reason = models.CharField(
    max_length=20,
    choices=DISCARD_REASONS,
    blank=True,
    null=True,
    verbose_name='Aussortierungsgrund',
    help_text='Grund für die Aussortierung (nur bei DISCARD-Transaktionen)'
)
```

**Discard Reason Choices:**
- `LOST` - Verloren (Lost)
- `DAMAGED` - Beschädigt (Damaged)
- `WORN_OUT` - Verschlissen (Worn out)
- `STOLEN` - Gestohlen (Stolen)
- `OTHER` - Sonstiges (Other)

**Validation Rules:**
- DISCARD transactions **must** have a `discard_reason`
- Non-DISCARD transactions **cannot** have a `discard_reason`

#### 2. API Serializer (`backend/inventory/api/serializers.py`)

**New Fields:**
- `discard_reason` - The reason code (LOST, DAMAGED, etc.)
- `discard_reason_display` - Human-readable reason text (Verloren, Beschädigt, etc.)

**Validation:**
- API-level validation ensures `discard_reason` is required for DISCARD transactions
- Returns HTTP 400 with clear error message if validation fails

#### 3. API ViewSet (`backend/inventory/api/viewsets.py`)

**New Endpoint:** `GET /api/v1/inventory/transactions/discard-statistics/`

Returns comprehensive statistics about discarded items:

```json
{
  "by_reason": [
    {
      "discard_reason": "LOST",
      "count": 15,
      "total_quantity": 42
    },
    {
      "discard_reason": "DAMAGED",
      "count": 8,
      "total_quantity": 12
    }
  ],
  "by_category": [
    {
      "category": "Bekleidung",
      "count": 18,
      "total_quantity": 35
    }
  ],
  "by_time_period": {
    "last_30_days": {
      "count": 5,
      "total_quantity": 10
    },
    "last_6_months": {
      "count": 18,
      "total_quantity": 42
    },
    "all_time": {
      "count": 23,
      "total_quantity": 54
    }
  },
  "recent_discards": [
    // ... last 10 DISCARD transactions
  ]
}
```

**New Filter:** Added `discard_reason` to transaction filters

```
GET /api/v1/inventory/transactions/?discard_reason=LOST
```

#### 4. Database Migration

Migration file: `backend/inventory/migrations/0009_transaction_discard_reason.py`

Run with:
```bash
cd backend
pipenv run python manage.py migrate inventory
```

### Frontend Changes

#### 1. TypeScript Types (`frontend/src/types/inventory.ts`)

**New Type:**
```typescript
export type DiscardReason = 'LOST' | 'DAMAGED' | 'WORN_OUT' | 'STOLEN' | 'OTHER'
```

**New Constant:**
```typescript
export const DISCARD_REASONS: { value: DiscardReason; label: string; icon: string }[] = [
  { value: 'LOST', label: 'Verloren', icon: 'pi-question-circle' },
  { value: 'DAMAGED', label: 'Beschädigt', icon: 'pi-exclamation-triangle' },
  { value: 'WORN_OUT', label: 'Verschlissen', icon: 'pi-clock' },
  { value: 'STOLEN', label: 'Gestohlen', icon: 'pi-ban' },
  { value: 'OTHER', label: 'Sonstiges', icon: 'pi-ellipsis-h' }
]
```

**Updated Interfaces:**
```typescript
interface Transaction {
  // ... existing fields
  discard_reason: DiscardReason | null
  discard_reason_display: string | null
}

interface TransactionCreate {
  // ... existing fields
  discard_reason?: DiscardReason | null
}

interface TransactionListParams {
  // ... existing fields
  discard_reason?: DiscardReason
}

interface DiscardStatistics {
  // ... structure matching backend response
}
```

#### 2. API Client (`frontend/src/api/inventory.ts`)

**New Method:**
```typescript
transactionsApi.getDiscardStatistics()
```

Returns discard statistics for dashboard/reporting views.

### Tests

Comprehensive test suite at `backend/inventory/tests/test_discard_functionality.py`:

- ✅ `DiscardReasonFieldTestCase` - Model validation
  - Validates DISCARD requires reason
  - Validates non-DISCARD cannot have reason
  - Tests all 5 reason types

- ✅ `DiscardStatisticsAPITestCase` - API endpoint
  - Tests endpoint accessibility
  - Validates response structure
  - Tests statistics grouping by reason
  - Tests transaction creation via API

- ✅ `DiscardFilteringTestCase` - Filtering
  - Tests filtering by discard_reason

**Run tests:**
```bash
cd backend
pipenv run python manage.py test inventory.tests.test_discard_functionality
```

All 9 tests pass! ✅

## Usage Examples

### Creating a Discard Transaction (Backend)

```python
from inventory.models import Transaction

# This will work
transaction = Transaction.objects.create(
    transaction_type='DISCARD',
    item=my_item,
    source=warehouse,
    quantity=5,
    discard_reason='LOST',  # Required!
    note='Lost during outdoor training',
    user=current_user
)

# This will raise ValidationError (missing discard_reason)
transaction = Transaction.objects.create(
    transaction_type='DISCARD',
    item=my_item,
    source=warehouse,
    quantity=5,
    # Missing discard_reason!
    user=current_user
)
```

### Creating a Discard Transaction (API)

```bash
# Will succeed
curl -X POST /api/v1/inventory/transactions/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_type": "DISCARD",
    "item": 123,
    "source": 45,
    "quantity": 3,
    "discard_reason": "DAMAGED",
    "note": "Torn during training exercise"
  }'

# Will return 400 error
curl -X POST /api/v1/inventory/transactions/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_type": "DISCARD",
    "item": 123,
    "source": 45,
    "quantity": 3,
    "note": "Missing discard_reason!"
  }'
```

### Frontend Usage (TypeScript)

```typescript
import { transactionsApi } from '@/api/inventory'
import { DISCARD_REASONS } from '@/types/inventory'

// Create discard transaction
const transaction = await transactionsApi.create({
  transaction_type: 'DISCARD',
  item: itemId,
  source: locationId,
  quantity: 2,
  discard_reason: 'LOST',
  note: 'Verloren beim Zeltlager'
})

// Get statistics
const stats = await transactionsApi.getDiscardStatistics()
console.log(`Total lost items: ${stats.by_reason.find(r => r.discard_reason === 'LOST')?.total_quantity}`)

// Filter by reason
const lostItems = await transactionsApi.list({
  transaction_type: 'DISCARD',
  discard_reason: 'LOST'
})
```

## Benefits

1. **Better Accountability**: Track exactly why items are being removed from inventory
2. **Loss Prevention**: Identify patterns (e.g., "we lose many items at outdoor events")
3. **Budget Planning**: Quantify losses vs. damage vs. normal wear
4. **Insurance Claims**: Document stolen/damaged items with proper categorization
5. **Reporting**: Built-in statistics endpoint for dashboards and reports

## Migration Path

### For Existing Data

Existing DISCARD transactions created before this feature will have `discard_reason = NULL`. 

**Options:**
1. **Do nothing** - They remain valid but without a reason
2. **Data migration** - Create a data migration to set all existing DISCARDs to `OTHER` or specific reason based on notes

Example data migration:
```python
from django.db import migrations

def set_default_discard_reasons(apps, schema_editor):
    Transaction = apps.get_model('inventory', 'Transaction')
    Transaction.objects.filter(
        transaction_type='DISCARD',
        discard_reason__isnull=True
    ).update(discard_reason='OTHER')

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0009_transaction_discard_reason'),
    ]
    
    operations = [
        migrations.RunPython(set_default_discard_reasons),
    ]
```

### For New Development

All new DISCARD transactions **must** provide a `discard_reason`. The API and model validation enforce this.

## Future Enhancements

Potential improvements:

1. **Custom Discard Reasons**: Allow organizations to define custom reasons beyond the 5 defaults
2. **Monetary Value Tracking**: Track the value of discarded items for financial reporting
3. **Photo Documentation**: Attach photos to DISCARD transactions (especially for DAMAGED/STOLEN)
4. **Approval Workflow**: Require approval for high-value discards
5. **Dashboard Widget**: Add discard statistics to the main dashboard
6. **Trend Analysis**: Graph discard trends over time by reason and category
7. **Email Notifications**: Alert admins when discard rate exceeds threshold

## Technical Notes

- **Database Column**: `VARCHAR(20)`, nullable for backward compatibility
- **API Field**: Included in transaction list/detail serializers
- **Permissions**: Uses existing transaction permissions (no new permissions added)
- **Performance**: Statistics endpoint uses Django aggregations (efficient)
- **Backward Compatibility**: Existing code continues to work; old DISCARD transactions remain valid

## Files Modified

### Backend
- ✅ `backend/inventory/models/stock.py` - Added discard_reason field and validation
- ✅ `backend/inventory/api/serializers.py` - Added field to serializer with validation
- ✅ `backend/inventory/api/viewsets.py` - Added statistics endpoint and filter
- ✅ `backend/inventory/migrations/0009_transaction_discard_reason.py` - Database migration
- ✅ `backend/inventory/tests/test_discard_functionality.py` - Comprehensive test suite

### Frontend
- ✅ `frontend/src/types/inventory.ts` - Added DiscardReason type and constants
- ✅ `frontend/src/api/inventory.ts` - Added getDiscardStatistics() method

## Deployment Checklist

- [x] Run migration: `pipenv run python manage.py migrate inventory`
- [x] Run tests: `pipenv run python manage.py test inventory.tests.test_discard_functionality`
- [ ] Update UI to include discard reason dropdown when creating DISCARD transactions
- [ ] Add dashboard widget to show discard statistics
- [ ] Document the new field in user manual/training materials
- [ ] (Optional) Create data migration for existing DISCARD transactions

---

**Created**: January 12, 2026
**Status**: ✅ Complete - Backend fully implemented and tested
**Next Steps**: Frontend UI components (transaction form, statistics dashboard)
