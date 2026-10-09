"""PORTAL-03.3: parallel decisions and submissions on PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase

from members.models import Member
from portal import change_requests as cr
from portal.models import ChangeLog, ChangeRequest

User = get_user_model()


def parallel(count, work):
    barrier = Barrier(count)

    def run(index):
        close_old_connections()
        try:
            barrier.wait(timeout=20)
            return work(index)
        except cr.ChangeRequestError as error:
            return error.code
        finally:
            # Healthy persistent connections must also close before the thread exits.
            connections.close_all()

    with ThreadPoolExecutor(max_workers=count) as executor:
        return list(executor.map(run, range(count)))


@skipUnless(connection.vendor == "postgresql", "Row locking requires PostgreSQL")
class ChangeRequestConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.member = Member.objects.create(name="Mia", lastname="Becker", city="Bonn")
        self.requester = User.objects.create_user("antrag", password="x", account_kind="portal")
        self.reviewers = [User.objects.create_user(f"pruefer{i}", password="x") for i in range(4)]

    def test_only_one_of_several_reviewers_decides(self):
        request, _ = cr.submit(self.member, {"city": "Köln"}, self.requester)
        results = parallel(4, lambda i: cr.decide(request, self.reviewers[i], {"city": "apply"}, version=1).status)
        self.assertEqual(results.count("applied"), 1)
        self.assertEqual(results.count("decided"), 3)
        self.assertEqual(ChangeLog.objects.count(), 1)

    def test_parallel_submissions_keep_one_open_request(self):
        results = parallel(8, lambda i: cr.submit(self.member, {"city": f"Ort {i}"}, self.requester)[0].pk)
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(ChangeRequest.objects.count(), 1)
        self.assertEqual(ChangeRequest.objects.get().version, 8)
