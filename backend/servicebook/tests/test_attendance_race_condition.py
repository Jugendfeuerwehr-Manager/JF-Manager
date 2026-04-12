"""Tests for attendance race condition fix."""
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from members.models import Member
from servicebook.models import Attendance, Service

User = get_user_model()


class AttendanceRaceConditionTestCase(TestCase):
    """Test that the attendance bulk update handles concurrent requests correctly."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create test user with staff and superuser permissions
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=self.user)

        # Create test members
        self.member1 = Member.objects.create(
            name='John',
            lastname='Doe'
        )
        self.member2 = Member.objects.create(
            name='Jane',
            lastname='Smith'
        )

        # Create test service
        start_time = datetime.now()
        self.service = Service.objects.create(
            start=start_time,
            end=start_time + timedelta(hours=2),
            topic='Test Service',
            place='Test Location'
        )

    def test_unique_constraint_prevents_duplicates(self):
        """Test that database constraint prevents duplicate attendance records."""
        # Create first attendance
        Attendance.objects.create(
            person=self.member1,
            service=self.service,
            state='A'
        )

        # Attempting to create duplicate should raise IntegrityError
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Attendance.objects.create(
                person=self.member1,
                service=self.service,
                state='E'
            )

    def test_bulk_update_handles_updates_correctly(self):
        """Test that bulk update uses update_or_create correctly."""
        # Create initial attendance
        Attendance.objects.create(
            person=self.member1,
            service=self.service,
            state='A'
        )

        # Update via bulk_update endpoint
        response = self.client.post(
            '/api/v1/servicebook/attendances/bulk_update/',
            {
                'service': self.service.id,
                'attendances': [
                    {'person_id': self.member1.id, 'state': 'E'},
                    {'person_id': self.member2.id, 'state': 'A'},
                ]
            },
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        # Check results
        result = response.json()
        self.assertEqual(result['updated'], 1)  # member1 was updated
        self.assertEqual(result['created'], 1)  # member2 was created

        # Verify state changes
        attendance1 = Attendance.objects.get(person=self.member1, service=self.service)
        self.assertEqual(attendance1.state, 'E')

        attendance2 = Attendance.objects.get(person=self.member2, service=self.service)
        self.assertEqual(attendance2.state, 'A')

    def test_bulk_update_with_delete(self):
        """Test that bulk update can delete attendance records."""
        # Create initial attendance
        Attendance.objects.create(
            person=self.member1,
            service=self.service,
            state='A'
        )
        Attendance.objects.create(
            person=self.member2,
            service=self.service,
            state='E'
        )

        # Delete one via bulk_update endpoint (state=None)
        response = self.client.post(
            '/api/v1/servicebook/attendances/bulk_update/',
            {
                'service': self.service.id,
                'attendances': [
                    {'person_id': self.member1.id, 'state': None},
                ]
            },
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        # Check results
        result = response.json()
        self.assertEqual(result['deleted'], 1)

        # Verify member1 attendance is deleted
        self.assertFalse(
            Attendance.objects.filter(
                person=self.member1,
                service=self.service
            ).exists()
        )

        # Verify member2 attendance still exists
        self.assertTrue(
            Attendance.objects.filter(
                person=self.member2,
                service=self.service
            ).exists()
        )
