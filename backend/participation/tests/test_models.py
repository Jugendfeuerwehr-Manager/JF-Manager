from datetime import date, time

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from departments.models import Department
from members.models import Member
from participation.models import ParticipationDefaults, Registration, RegistrationEvent, SessionParticipation
from training.models import TrainingSession


class ModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(name="A", code="a")
        cls.session = TrainingSession.objects.create(
            title="Übung", date=date(2030, 1, 5), start_time=time(18), end_time=time(20), department=cls.dept
        )
        cls.member = Member.objects.create(name="Mia", lastname="Test")

    def test_defaults_are_unique_per_department_and_organisation(self):
        ParticipationDefaults.objects.create(department=self.dept)
        ParticipationDefaults.objects.create(department=None)
        for department in (self.dept, None):
            with self.subTest(department=department), self.assertRaises(IntegrityError), transaction.atomic():
                ParticipationDefaults.objects.create(department=department)

    def test_hard_defaults(self):
        row = ParticipationDefaults.objects.create()
        self.assertEqual((row.registration_offset_h, row.cancellation_offset_h, row.mode), (48, 2, "opt_out"))

    def test_session_participation_defaults(self):
        row = SessionParticipation.objects.create(session=self.session)
        self.assertTrue(row.portal_visible)
        self.assertEqual((row.eligibility, row.revision), ({}, 1))

    def test_one_registration_per_member_and_session(self):
        now = timezone.now()
        Registration.objects.create(
            session=self.session, member=self.member, state="registered", source="staff", state_changed_at=now
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Registration.objects.create(
                session=self.session, member=self.member, state="cancelled", source="staff", state_changed_at=now
            )

    def test_events_are_append_only(self):
        now = timezone.now()
        reg = Registration.objects.create(
            session=self.session, member=self.member, state="registered", source="staff", state_changed_at=now
        )
        event = RegistrationEvent.objects.create(registration=reg, to_state="registered", at=now, via="staff")
        with self.assertRaises(ValueError):
            event.save()
