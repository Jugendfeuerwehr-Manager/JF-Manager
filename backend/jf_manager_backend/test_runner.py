"""Keep cached authentication attempts and preferences isolated between tests
and let the plain-HTTP test client reach views."""

from unittest import TextTestResult

from django.conf import settings
from django.core.cache import cache
from django.test.runner import DiscoverRunner


class CacheIsolatedResult(TextTestResult):
    def startTest(self, test):
        cache.clear()
        super().startTest(test)


class CacheIsolatedRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        # The test client speaks plain HTTP; redirect behaviour has its own tests.
        settings.SECURE_SSL_REDIRECT = False

    def get_resultclass(self):
        return super().get_resultclass() or CacheIsolatedResult
