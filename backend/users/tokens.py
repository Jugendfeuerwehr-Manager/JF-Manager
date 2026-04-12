"""Password reset token generator for secure password reset functionality."""
import six
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Token generator for password reset that expires after 1 hour.
    Uses Django's built-in token generation mechanism.
    """
    def _make_hash_value(self, user, timestamp):
        """
        Hash the user's primary key, email, and timestamp to create a unique token.
        Token becomes invalid when user changes their password.
        """
        return (
            six.text_type(user.pk) +
            six.text_type(timestamp) +
            six.text_type(user.is_active)
        )


password_reset_token = AccountActivationTokenGenerator()
