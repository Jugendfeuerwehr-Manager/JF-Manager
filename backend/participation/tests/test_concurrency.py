from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest import skipUnless

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase

from departments.models import Department
from participation.models import Registration
from participation.service import set_registration

from .helpers import berlin, configure, make_member, make_session


@skipUnless(connection.vendor == "postgresql", "Row locking on the session requires PostgreSQL")
class RegistrationConcurrencyTests(TransactionTestCase):
    def test_sixty_parallel_registrations_on_three_places(self):
        dept = Department.objects.create(name="A", code="a")
        session = make_session(dept)
        configure(session, mode="opt_in", max_participants=3)
        members = [make_member(dept, f"M{i}") for i in range(60)]
        now = berlin(2030, 3, 7, 12)
        barrier = Barrier(len(members))

        def register(member):
            close_old_connections()
            try:
                barrier.wait(timeout=20)
                return set_registration(session.pk, member.pk, "registered", actor=None, source="staff", now=now)[
                    0
                ].state
            finally:
                # Healthy persistent connections must also close before the thread exits.
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(members)) as executor:
            results = list(executor.map(register, members))
        self.assertEqual(results.count("registered"), 3)
        self.assertEqual(results.count("waitlisted"), 57)
        self.assertEqual(Registration.objects.filter(session=session, state="registered").count(), 3)
        self.assertEqual(Registration.objects.filter(session=session).count(), 60)

    def test_parallel_cancellations_promote_each_waiting_person_once(self):
        dept = Department.objects.create(name="A", code="a")
        session = make_session(dept)
        configure(session, mode="opt_in", max_participants=2)
        members = [make_member(dept, f"M{i}") for i in range(6)]
        for i, member in enumerate(members):
            set_registration(
                session.pk,
                member.pk,
                "registered",
                actor=None,
                source="staff",
                now=berlin(2030, 3, 1, 12) + timedelta(minutes=i),
            )
        barrier = Barrier(2)

        def cancel(member):
            close_old_connections()
            try:
                barrier.wait(timeout=20)
                set_registration(
                    session.pk, member.pk, "cancelled", actor=None, source="staff", now=berlin(2030, 3, 7, 12)
                )
            finally:
                # Healthy persistent connections must also close before the thread exits.
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(cancel, members[:2]))
        self.assertEqual(Registration.objects.filter(session=session, state="registered").count(), 2)
        self.assertEqual(Registration.objects.filter(session=session, state="waitlisted").count(), 2)
