from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model

User = get_user_model()

TEST_EMAIL_SETTINGS = {
    'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
}


class CustomPasswordResetViewTests(TestCase):
    """Tests for CustomPasswordResetView using SITE_URL for reset link domain."""

    def setUp(self):
        # A superuser is required so that SetupMiddleware does not redirect requests.
        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123',
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='OldPassword123',
        )

    @override_settings(SITE_URL='https://myjfmanager.example.com', **TEST_EMAIL_SETTINGS)
    def test_reset_link_uses_site_url_domain(self):
        """Reset email should contain the domain from SITE_URL, not localhost."""
        response = self.client.post(
            '/accounts/password_reset/',
            {'email': 'testuser@example.com'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        self.assertIn('myjfmanager.example.com', email_body)
        self.assertNotIn('localhost', email_body)

    @override_settings(SITE_URL='http://myjfmanager.example.com', **TEST_EMAIL_SETTINGS)
    def test_reset_link_uses_http_when_site_url_is_http(self):
        """When SITE_URL uses http, the link in the email should use http."""
        self.client.post(
            '/accounts/password_reset/',
            {'email': 'testuser@example.com'},
        )
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        self.assertIn('http://myjfmanager.example.com', email_body)

    @override_settings(SITE_URL='', **TEST_EMAIL_SETTINGS)
    def test_reset_link_falls_back_when_site_url_empty(self):
        """When SITE_URL is empty the view falls back to Django's default behaviour."""
        response = self.client.post(
            '/accounts/password_reset/',
            {'email': 'testuser@example.com'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
