"""Single-use password reset tokens invalidated by password and email changes."""

from django.contrib.auth.tokens import PasswordResetTokenGenerator

password_reset_token = PasswordResetTokenGenerator()
