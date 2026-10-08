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
        # Unit fixtures control their own catalog. Installation itself is tested
        # explicitly with ROLE_SEED_ON_MIGRATE enabled, including post_migrate.
        self._role_seed_on_migrate = getattr(settings, "ROLE_SEED_ON_MIGRATE", True)
        settings.ROLE_SEED_ON_MIGRATE = False

    def teardown_test_environment(self, **kwargs):
        settings.ROLE_SEED_ON_MIGRATE = self._role_seed_on_migrate
        super().teardown_test_environment(**kwargs)

    def get_resultclass(self):
        return super().get_resultclass() or CacheIsolatedResult
