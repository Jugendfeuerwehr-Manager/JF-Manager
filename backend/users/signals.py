"""Revoke legacy API credentials when a password changes or an account is disabled."""

from django.conf import settings
from django.db.models.signals import pre_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


@receiver(pre_save, sender=settings.AUTH_USER_MODEL)
def revoke_credentials(sender, instance, **kwargs):
    if not instance.pk:
        return
    previous = sender.objects.filter(pk=instance.pk).values("password", "is_active").first()
    if previous and (previous["password"] != instance.password or not instance.is_active):
        Token.objects.filter(user_id=instance.pk).delete()
