import os
import uuid

from django.conf import settings
from django.db import models

from .group import Group
from .member import Member


def get_email_attachment_path(instance, filename):
    """Generate a unique file path for email attachments."""
    ext = filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join("email_attachments", unique_filename)


class EmailMessage(models.Model):
    """
    Model to store outgoing email messages sent to members and their parents.
    Tracks all emails sent through the system for history and auditing.
    """

    STATUS_CHOICES = [
        ("draft", "Entwurf"),
        ("sending", "Wird gesendet"),
        ("sent", "Gesendet"),
        ("failed", "Fehlgeschlagen"),
        ("partial", "Teilweise gesendet"),
    ]

    RECIPIENT_TYPE_CHOICES = [
        ("all", "Alle Mitglieder"),
        ("group", "Gruppe"),
        ("individual", "Einzelnes Mitglied"),
    ]

    # Metadata
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_emails",
        verbose_name="Absender",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Gesendet am")

    # Email content
    subject = models.CharField(max_length=500, verbose_name="Betreff")
    body_html = models.TextField(verbose_name="Nachricht (HTML)")
    body_text = models.TextField(blank=True, verbose_name="Nachricht (Text)")

    # Recipient selection
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPE_CHOICES, verbose_name="Empfängertyp")
    recipient_group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Empfängergruppe"
    )
    recipient_member = models.ForeignKey(
        Member, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Empfängermitglied"
    )

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft", verbose_name="Status")
    total_recipients = models.IntegerField(default=0, verbose_name="Anzahl Empfänger")
    successful_sends = models.IntegerField(default=0, verbose_name="Erfolgreich gesendet")
    failed_sends = models.IntegerField(default=0, verbose_name="Fehlgeschlagen")

    # Department scoping
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Abteilung",
        related_name="emails",
    )

    # Error tracking
    error_message = models.TextField(blank=True, verbose_name="Fehlermeldung")

    class Meta:
        verbose_name = "E-Mail-Nachricht"
        verbose_name_plural = "E-Mail-Nachrichten"
        ordering = ["-created_at"]
        permissions = [
            ("can_send_member_emails", "Can send emails to members"),
        ]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["sender", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.subject} - {self.get_status_display()}"


class EmailRecipient(models.Model):
    """
    Tracks individual recipients for each email message.
    Stores delivery status per recipient for detailed tracking.
    """

    STATUS_CHOICES = [
        ("pending", "Ausstehend"),
        ("sent", "Gesendet"),
        ("failed", "Fehlgeschlagen"),
    ]

    email_message = models.ForeignKey(
        EmailMessage, on_delete=models.CASCADE, related_name="recipients", verbose_name="E-Mail-Nachricht"
    )
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Mitglied")
    email_address = models.EmailField(verbose_name="E-Mail-Adresse")
    recipient_name = models.CharField(max_length=400, verbose_name="Empfängername")

    # Personalization - stores the rendered content for this specific recipient
    personalized_body_html = models.TextField(blank=True, verbose_name="Personalisierte Nachricht (HTML)")
    personalized_body_text = models.TextField(blank=True, verbose_name="Personalisierte Nachricht (Text)")

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Status")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Gesendet am")
    error_message = models.TextField(blank=True, verbose_name="Fehlermeldung")

    class Meta:
        verbose_name = "E-Mail-Empfänger"
        verbose_name_plural = "E-Mail-Empfänger"
        ordering = ["email_address"]
        indexes = [
            models.Index(fields=["email_message", "status"]),
            models.Index(fields=["member"]),
        ]

    def __str__(self):
        return f"{self.recipient_name} <{self.email_address}>"


class EmailAttachment(models.Model):
    """
    Stores file attachments for email messages.
    """

    email_message = models.ForeignKey(
        EmailMessage, on_delete=models.CASCADE, related_name="attachments", verbose_name="E-Mail-Nachricht"
    )
    file = models.FileField(upload_to=get_email_attachment_path, verbose_name="Datei")
    original_filename = models.CharField(max_length=255, verbose_name="Originaldateiname")
    file_size = models.PositiveIntegerField(default=0, verbose_name="Dateigröße (Bytes)")
    content_type = models.CharField(max_length=100, blank=True, verbose_name="MIME-Typ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")

    class Meta:
        verbose_name = "E-Mail-Anhang"
        verbose_name_plural = "E-Mail-Anhänge"
        ordering = ["created_at"]

    def __str__(self):
        return self.original_filename
