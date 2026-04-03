"""
Unit tests for inventory discard functionality

Tests the new discard_reason field and discard statistics endpoint.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from inventory.models import (
    Category,
    Item,
    StorageLocation,
    Stock,
    Transaction,
)

User = get_user_model()


class DiscardReasonFieldTestCase(TestCase):
    """Test discard_reason field validation"""

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            schema={}
        )
        self.item = Item.objects.create(
            name='Test Item',
            category=self.category,
            base_unit='Stück'
        )
        self.storage_location = StorageLocation.objects.create(
            name='Main Storage',
            is_member=False
        )
        # Create initial stock
        Stock.objects.create(
            item=self.item,
            location=self.storage_location,
            quantity=100
        )

    def test_discard_transaction_requires_reason(self):
        """DISCARD transactions must have a discard_reason"""
        transaction = Transaction(
            transaction_type='DISCARD',
            item=self.item,
            source=self.storage_location,
            quantity=5,
            user=self.user
        )
        
        # Should raise ValidationError because discard_reason is missing
        with self.assertRaises(ValidationError):
            transaction.clean()

    def test_discard_transaction_with_reason_valid(self):
        """DISCARD transactions with discard_reason should be valid"""
        transaction = Transaction(
            transaction_type='DISCARD',
            item=self.item,
            source=self.storage_location,
            quantity=5,
            discard_reason='LOST',
            user=self.user
        )
        
        # Should not raise
        transaction.clean()
        transaction.save()
        
        self.assertEqual(transaction.discard_reason, 'LOST')
        self.assertEqual(transaction.get_discard_reason_display(), 'Verloren')

    def test_non_discard_transaction_cannot_have_reason(self):
        """Non-DISCARD transactions cannot have discard_reason"""
        transaction = Transaction(
            transaction_type='IN',
            item=self.item,
            target=self.storage_location,
            quantity=5,
            discard_reason='LOST',  # Should not be allowed
            user=self.user
        )
        
        # Should raise ValidationError
        with self.assertRaises(ValidationError):
            transaction.clean()

    def test_all_discard_reasons_valid(self):
        """Test all discard reason choices are valid"""
        reasons = ['LOST', 'DAMAGED', 'WORN_OUT', 'STOLEN', 'OTHER']
        
        for reason in reasons:
            transaction = Transaction.objects.create(
                transaction_type='DISCARD',
                item=self.item,
                source=self.storage_location,
                quantity=1,
                discard_reason=reason,
                user=self.user,
                note=f'Test {reason}'
            )
            self.assertEqual(transaction.discard_reason, reason)


class DiscardStatisticsAPITestCase(TestCase):
    """Test the discard statistics endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            schema={}
        )
        self.item = Item.objects.create(
            name='Test Item',
            category=self.category,
            base_unit='Stück'
        )
        self.storage_location = StorageLocation.objects.create(
            name='Main Storage',
            is_member=False
        )

    def test_discard_statistics_endpoint_exists(self):
        """Endpoint should be accessible"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/inventory/transactions/discard-statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_discard_statistics_structure(self):
        """Response should have correct structure"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/inventory/transactions/discard-statistics/')
        
        data = response.json()
        self.assertIn('by_reason', data)
        self.assertIn('by_category', data)
        self.assertIn('by_time_period', data)
        self.assertIn('recent_discards', data)
        
        # Time period breakdown
        self.assertIn('last_30_days', data['by_time_period'])
        self.assertIn('last_6_months', data['by_time_period'])
        self.assertIn('all_time', data['by_time_period'])

    def test_discard_statistics_by_reason(self):
        """Statistics should group by discard reason"""
        # Create stock first
        Stock.objects.create(item=self.item, location=self.storage_location, quantity=100)
        
        # Create discards with different reasons
        Transaction.objects.create(
            transaction_type='DISCARD',
            item=self.item,
            source=self.storage_location,
            quantity=5,
            discard_reason='LOST',
            user=self.user
        )
        Transaction.objects.create(
            transaction_type='DISCARD',
            item=self.item,
            source=self.storage_location,
            quantity=3,
            discard_reason='LOST',
            user=self.user
        )
        Transaction.objects.create(
            transaction_type='DISCARD',
            item=self.item,
            source=self.storage_location,
            quantity=2,
            discard_reason='DAMAGED',
            user=self.user
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/inventory/transactions/discard-statistics/')
        data = response.json()
        
        # Check by_reason breakdown
        by_reason = {entry['discard_reason']: entry for entry in data['by_reason']}
        
        self.assertIn('LOST', by_reason)
        self.assertEqual(by_reason['LOST']['count'], 2)
        self.assertEqual(by_reason['LOST']['total_quantity'], 8)
        
        self.assertIn('DAMAGED', by_reason)
        self.assertEqual(by_reason['DAMAGED']['count'], 1)
        self.assertEqual(by_reason['DAMAGED']['total_quantity'], 2)

    def test_discard_transaction_creation_via_api(self):
        """Creating DISCARD transaction via API should require discard_reason"""
        # Create stock first
        Stock.objects.create(item=self.item, location=self.storage_location, quantity=100)
        
        self.client.force_authenticate(user=self.user)
        
        # Try without discard_reason - should fail
        response = self.client.post('/api/v1/inventory/transactions/', {
            'transaction_type': 'DISCARD',
            'item': self.item.id,
            'source': self.storage_location.id,
            'quantity': 5,
            'note': 'Test discard'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # With discard_reason - should succeed
        response = self.client.post('/api/v1/inventory/transactions/', {
            'transaction_type': 'DISCARD',
            'item': self.item.id,
            'source': self.storage_location.id,
            'quantity': 5,
            'discard_reason': 'LOST',
            'note': 'Lost during training'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        created = response.json()
        self.assertEqual(created['discard_reason'], 'LOST')
        self.assertEqual(created['discard_reason_display'], 'Verloren')


class DiscardFilteringTestCase(TestCase):
    """Test filtering transactions by discard_reason"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            schema={}
        )
        self.item = Item.objects.create(
            name='Test Item',
            category=self.category,
            base_unit='Stück'
        )
        self.storage_location = StorageLocation.objects.create(
            name='Main Storage',
            is_member=False
        )

    def test_filter_transactions_by_discard_reason(self):
        """Should be able to filter transactions by discard_reason"""
        # Create stock first
        Stock.objects.create(item=self.item, location=self.storage_location, quantity=100)
        
        # Create transactions with different reasons
        Transaction.objects.create(
            transaction_type='DISCARD',
            item=self.item,
            source=self.storage_location,
            quantity=5,
            discard_reason='LOST',
            user=self.user
        )
        Transaction.objects.create(
            transaction_type='DISCARD',
            item=self.item,
            source=self.storage_location,
            quantity=3,
            discard_reason='DAMAGED',
            user=self.user
        )
        
        self.client.force_authenticate(user=self.user)
        
        # Filter by LOST
        response = self.client.get('/api/v1/inventory/transactions/', {
            'discard_reason': 'LOST'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['discard_reason'], 'LOST')
        
        # Filter by DAMAGED
        response = self.client.get('/api/v1/inventory/transactions/', {
            'discard_reason': 'DAMAGED'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['discard_reason'], 'DAMAGED')

