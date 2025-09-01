from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from qualifications.models import QualificationType, Qualification
from members.models import Member, Group, Status

User = get_user_model()


class QualificationTypeModelTest(TestCase):
    def test_create_qualification_type(self):
        """Test der Erstellung eines Qualifikationstyps"""
        qual_type = QualificationType.objects.create(
            name="Grundlehrgang",
            expires=True,
            validity_period=24,
            description="Grundausbildung für Jugendfeuerwehr"
        )
        
        self.assertEqual(qual_type.name, "Grundlehrgang")
        self.assertTrue(qual_type.expires)
        self.assertEqual(qual_type.validity_period, 24)
        self.assertEqual(str(qual_type), "Grundlehrgang")

    def test_qualification_type_validation(self):
        """Test der Validierung bei Qualifikationstypen"""
        # Expires=True ohne validity_period sollte einen Fehler auslösen
        qual_type = QualificationType(
            name="Test",
            expires=True,
            validity_period=None
        )
        
        with self.assertRaises(ValidationError):
            qual_type.clean()

    def test_qualification_type_no_expiry(self):
        """Test für nicht-ablaufende Qualifikationstypen"""
        qual_type = QualificationType.objects.create(
            name="Lifetime Certificate",
            expires=False
        )
        
        self.assertFalse(qual_type.expires)
        self.assertIsNone(qual_type.validity_period)


class QualificationModelTest(TestCase):
    def setUp(self):
        """Setup für Qualification Tests"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        # Member erstellen
        group = Group.objects.create(name="Jugendfeuerwehr")
        status = Status.objects.create(name="Aktiv")
        self.member = Member.objects.create(
            name="Max",
            lastname="Mustermann",
            group=group,
            status=status
        )
        
        # Qualifikationstypen
        self.expiring_type = QualificationType.objects.create(
            name="Sprechfunk",
            expires=True,
            validity_period=24
        )
        
        self.permanent_type = QualificationType.objects.create(
            name="Grundlehrgang",
            expires=False
        )

    def test_create_qualification_for_user(self):
        """Test der Erstellung einer Qualifikation für einen User"""
        qualification = Qualification.objects.create(
            type=self.expiring_type,
            user=self.user,
            date_acquired=date.today(),
            issued_by="Feuerwehrschule"
        )
        
        self.assertEqual(qualification.get_person_name(), "Test User")
        self.assertEqual(qualification.get_person(), self.user)
        self.assertFalse(qualification.is_expired())

    def test_create_qualification_for_member(self):
        """Test der Erstellung einer Qualifikation für ein Member"""
        qualification = Qualification.objects.create(
            type=self.permanent_type,
            member=self.member,
            date_acquired=date.today()
        )
        
        self.assertEqual(qualification.get_person_name(), "Max Mustermann")
        self.assertEqual(qualification.get_person(), self.member)
        self.assertFalse(qualification.is_expired())

    def test_automatic_expiry_date_calculation(self):
        """Test der automatischen Berechnung des Ablaufdatums"""
        acquired_date = date(2023, 1, 15)
        qualification = Qualification.objects.create(
            type=self.expiring_type,
            user=self.user,
            date_acquired=acquired_date
        )
        
        expected_expiry = acquired_date + relativedelta(months=24)
        self.assertEqual(qualification.date_expires, expected_expiry)

    def test_qualification_expiry_status(self):
        """Test der Ablaufstatus-Methoden"""
        # Abgelaufene Qualifikation
        expired_qualification = Qualification.objects.create(
            type=self.expiring_type,
            user=self.user,
            date_acquired=date.today() - timedelta(days=800),
            date_expires=date.today() - timedelta(days=30)
        )
        
        self.assertTrue(expired_qualification.is_expired())
        # Abgelaufene Qualifikationen sollten nicht als "bald ablaufend" gelten
        self.assertFalse(expired_qualification.expires_soon())
        self.assertEqual(expired_qualification.get_status_class(), 'table-danger')
        
        # Bald ablaufende Qualifikation (nicht abgelaufen, aber läuft in weniger als 30 Tagen ab)
        expiring_qualification = Qualification.objects.create(
            type=self.expiring_type,
            member=self.member,
            date_acquired=date.today() - timedelta(days=700),
            date_expires=date.today() + timedelta(days=15)
        )
        
        self.assertFalse(expiring_qualification.is_expired())
        self.assertTrue(expiring_qualification.expires_soon())
        self.assertEqual(expiring_qualification.get_status_class(), 'table-warning')

    def test_qualification_validation(self):
        """Test der Validierung bei Qualifikationen"""
        # Keine Person ausgewählt
        qualification = Qualification(
            type=self.permanent_type,
            date_acquired=date.today()
        )
        
        with self.assertRaises(ValidationError):
            qualification.clean()
        
        # Beide Personen ausgewählt
        qualification = Qualification(
            type=self.permanent_type,
            user=self.user,
            member=self.member,
            date_acquired=date.today()
        )
        
        with self.assertRaises(ValidationError):
            qualification.clean()

    def test_qualification_string_representation(self):
        """Test der String-Repräsentation"""
        qualification = Qualification.objects.create(
            type=self.permanent_type,
            user=self.user,
            date_acquired=date.today()
        )
        
        expected_str = f"Test User - {self.permanent_type.name}"
        self.assertEqual(str(qualification), expected_str)
