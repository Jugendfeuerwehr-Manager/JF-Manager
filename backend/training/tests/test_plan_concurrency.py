from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from training.models import TrainingBlock, TrainingSession


@skipUnless(connection.vendor == "postgresql", "Parent row locking requires PostgreSQL")
class PlanConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="concurrent-plan")
        self.session = TrainingSession.objects.create(
            title="Parallel",
            date=date(2030, 1, 1),
            start_time=time(18),
            end_time=time(20),
        )
        self.blocks = [TrainingBlock.objects.create(session=self.session, title=f"Block {i}") for i in range(2)]

    def parallel(self, operations):
        barrier = Barrier(len(operations))

        def run(operation):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(get_user_model().objects.get(pk=self.user.pk))
                barrier.wait(timeout=10)
                return operation(client)
            finally:
                # Healthy persistent connections must also close before the thread exits.
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(operations)) as executor:
            return list(executor.map(run, operations))

    def test_two_complete_drafts_have_one_winner_and_one_conflict(self):
        def save(client):
            response = client.put(
                f"/api/v1/training/sessions/{self.session.pk}/plan/",
                {
                    "expected_revision": 1,
                    "session": {
                        "title": "Gespeichert",
                        "date": "2030-01-01",
                        "start_time": "18:00:00",
                        "end_time": "20:00:00",
                    },
                    "blocks": [{"id": block.pk, "title": block.title, "duration_minutes": 15} for block in self.blocks],
                },
                format="json",
            )
            return response.status_code

        self.assertEqual(sorted(self.parallel([save, save])), [200, 409])
        self.session.refresh_from_db()
        self.assertEqual(self.session.revision, 2)
        self.assertEqual(self.session.blocks.count(), 2)

    def test_parallel_legacy_moves_do_not_lose_revision_increments(self):
        def move(block):
            return lambda client: (
                client.patch(
                    f"/api/v1/training/blocks/{block.pk}/move/", {"start_offset_minutes": 30}, format="json"
                ).status_code
            )

        self.assertEqual(self.parallel([move(block) for block in self.blocks]), [200, 200])
        self.session.refresh_from_db()
        self.assertEqual(self.session.revision, 3)
        self.assertEqual(list(self.session.blocks.values_list("start_offset_minutes", flat=True)), [30, 30])
