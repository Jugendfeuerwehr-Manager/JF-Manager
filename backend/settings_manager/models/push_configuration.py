from django.db import models

from jf_manager_backend.encrypted_fields import StrictEncryptedCharField


class PushConfiguration(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    enabled = models.BooleanField(default=False)
    public_key = models.TextField(blank=True, default="")
    private_key = StrictEncryptedCharField(max_length=512, blank=True, default="")
    subject = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="push_configuration_singleton")]
