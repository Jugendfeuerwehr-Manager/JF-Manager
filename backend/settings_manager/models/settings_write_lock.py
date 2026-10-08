from django.db import models


class SettingsWriteLock(models.Model):
    """Serialize category patches so validation sees the same state as saving."""

    category = models.CharField(max_length=32, primary_key=True)
