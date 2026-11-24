from django.conf import settings
from django.db import models
from django.utils import timezone


class AdmissionVoucher(models.Model):
    """A one-time code that opens one published form for one prospective member.

    Only the SHA-256 of the code is stored; the code itself is shown once when created.
    """

    form = models.ForeignKey("admissions.AdmissionForm", on_delete=models.CASCADE, related_name="vouchers")
    department = models.ForeignKey(
        "departments.Department", on_delete=models.CASCADE, related_name="admission_vouchers"
    )
    code_hash = models.CharField(max_length=64, unique=True)
    code_hint = models.CharField(max_length=4, verbose_name="Code-Ende")
    label = models.CharField(max_length=200, blank=True, verbose_name="Für")
    prefill = models.JSONField(default=dict, blank=True, verbose_name="Vorbelegung")
    expires_at = models.DateTimeField(verbose_name="Gültig bis")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Eingelöst am")
    revoked_at = models.DateTimeField(null=True, blank=True, verbose_name="Widerrufen am")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "Aufnahme-Voucher"
        verbose_name_plural = "Aufnahme-Voucher"
        ordering = ["-created_at"]

    def __str__(self):
        return f"…{self.code_hint} ({self.label or self.form})"

    @property
    def state(self):
        if self.revoked_at:
            return "revoked"
        if self.used_at:
            return "used"
        if self.expires_at <= timezone.now():
            return "expired"
        return "open"
