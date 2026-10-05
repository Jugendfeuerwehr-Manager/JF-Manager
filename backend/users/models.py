from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from phonenumber_field.modelfields import PhoneNumberField

from jf_manager_backend.encrypted_fields import StrictEncryptedCharField


# Create your models here.
class CustomUser(AbstractUser):
    # add additional fields in here

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["oidc_issuer", "oidc_subject"],
                condition=~models.Q(oidc_subject=""),
                name="unique_oidc_identity",
            )
        ]

    class AuthSource(models.TextChoices):
        LOCAL = "local", "Lokal"
        LDAP = "ldap", "LDAP"
        OIDC = "oidc", "OIDC"

    auth_source = models.CharField(
        max_length=10,
        choices=AuthSource.choices,
        default=AuthSource.LOCAL,
        verbose_name="Authentifizierungsquelle",
        help_text="Gibt an, ob der Benutzer lokal oder über ein externes System (LDAP/OIDC) verwaltet wird.",
    )

    oidc_issuer = models.CharField(max_length=500, blank=True, default="", editable=False)
    oidc_subject = models.CharField(max_length=255, blank=True, default="", editable=False)

    dsgvo_internal = models.BooleanField(default=False)
    dsgvo_external = models.BooleanField(default=False)

    phone = PhoneNumberField(blank=True)
    mobile_phone = PhoneNumberField(blank=True)
    street = models.CharField(max_length=200, blank=True, default="")
    zip_code = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=200, blank=True, default="")

    # TODO: Add pre_delete hook to make sure to remove the file, not just the DB Recoard.
    avatar = models.ImageField(blank=True)

    # Email signature for bulk emails
    email_signature = models.TextField(
        blank=True, default="", verbose_name="E-Mail-Signatur", help_text="Ihre persönliche Signatur für E-Mails"
    )

    THEME_MODE_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
        ("system", "System"),
    ]
    theme_mode = models.CharField(
        max_length=10,
        choices=THEME_MODE_CHOICES,
        default="system",
        verbose_name="Theme-Modus",
        help_text="Bevorzugter Farbmodus (Hell, Dunkel, System)",
    )

    favorite_department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="favorite_users",
        verbose_name="Bevorzugte Abteilung",
        help_text="Wird beim Login als Standard-Abteilung gewählt",
    )

    def __str__(self):
        if self.last_name and self.first_name:
            return self.get_full_name()
        else:
            return self.username

    def get_absolute_url(self):
        return reverse("users:profile", kwargs={"pk": self.pk})

    """
    As we do not want users to save their 10MB DSLR Picutres on our Disk, we compress them on save.
    """

    def save(self, *args, **kwargs):
        if self.avatar and not self.avatar._committed:
            from jf_manager_backend.upload_safety import clean_avatar

            self.avatar = clean_avatar(self.avatar)
        super().save(*args, **kwargs)


class MFADevice(models.Model):
    """TOTP authenticator of one user; the shared secret is stored encrypted."""

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="mfa_device")
    secret = StrictEncryptedCharField(max_length=64)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    # Highest accepted TOTP time step; codes at or below it are replays.
    last_used_step = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "MFA-Gerät"
        verbose_name_plural = "MFA-Geräte"

    @property
    def is_confirmed(self):
        return self.confirmed_at is not None


class MFARecoveryCode(models.Model):
    """One-time recovery code; only a salted SHA-256 digest is stored."""

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="mfa_recovery_codes")
    salt = models.CharField(max_length=32)
    code_hash = models.CharField(max_length=64)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "MFA-Wiederherstellungscode"
        verbose_name_plural = "MFA-Wiederherstellungscodes"
