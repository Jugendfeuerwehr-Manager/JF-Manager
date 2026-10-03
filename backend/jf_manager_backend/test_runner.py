"""Keep cached authentication attempts and preferences isolated between tests."""

from unittest import TextTestResult

from django.core.cache import cache
from django.test.runner import DiscoverRunner


class CacheIsolatedResult(TextTestResult):
    def startTest(self, test):
        cache.clear()
        super().startTest(test)


class CacheIsolatedRunner(DiscoverRunner):
    def get_resultclass(self):
        return super().get_resultclass() or CacheIsolatedResult
