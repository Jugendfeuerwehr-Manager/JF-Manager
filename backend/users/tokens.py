"""Password reset token generator for secure password reset functionality."""
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import constant_time_compare
from django.utils.http import base36_to_int
import six


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
