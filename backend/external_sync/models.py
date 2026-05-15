from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class SyncJob(models.Model):
    class Provider(models.TextChoices):
        SPOND = "spond", "Spond"
        HI_ORG = "hi_org", "Hi-Org"

    class Scope(models.TextChoices):
        ORGANIZATION = "organization", "Organisation"
        DEPARTMENT = "department", "Abteilung"

    class RunMode(models.TextChoices):
        MANUAL = "manual", "Nur manuell"
        INTERVAL = "interval", "Intervall"

    class DeletionMode(models.TextChoices):
        REVIEW = "review", "Zur Prüfung markieren"
        AUTO_DELETE = "auto_delete", "Automatisch löschen"

    class SpondOperationMode(models.TextChoices):
        GROUPS_TO_GROUPS = "groups_to_groups", "Spond-Gruppen zu Gruppen"
        GROUPS_TO_DEPARTMENTS = "groups_to_departments", "Spond-Gruppen zu Abteilungen"
        MEMBERS_ONLY = "members_only", "Nur Mitglieder"

    name = models.CharField(max_length=200, verbose_name="Name")
    provider = models.CharField(max_length=30, choices=Provider.choices, verbose_name="Quelle")
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.ORGANIZATION, verbose_name="Geltung")
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sync_jobs",
        verbose_name="Abteilung",
    )
    run_mode = models.CharField(
        max_length=20, choices=RunMode.choices, default=RunMode.MANUAL, verbose_name="Ausführung"
    )
    interval_minutes = models.PositiveIntegerField(null=True, blank=True, verbose_name="Intervall (Minuten)")
    deletion_mode = models.CharField(
        max_length=20,
        choices=DeletionMode.choices,
        default=DeletionMode.REVIEW,
        verbose_name="Löschmodus",
    )
    enabled = models.BooleanField(default=True, verbose_name="Aktiv")
    config = models.JSONField(default=dict, blank=True, verbose_name="Konfiguration")
    credentials = models.JSONField(default=dict, blank=True, verbose_name="Zugangsdaten")
    created_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_sync_jobs",
        verbose_name="Erstellt von",
    )
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name="Letzte Ausführung")
    next_run_at = models.DateTimeField(null=True, blank=True, verbose_name="Nächste Ausführung")
    last_success_at = models.DateTimeField(null=True, blank=True, verbose_name="Letzter Erfolg")
    last_error = models.TextField(blank=True, verbose_name="Letzter Fehler")
    last_tested_at = models.DateTimeField(null=True, blank=True, verbose_name="Zuletzt getestet")
    last_test_status = models.BooleanField(null=True, blank=True, verbose_name="Letztes Testergebnis")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "Synchronisationsjob"
        verbose_name_plural = "Synchronisationsjobs"
        ordering = ["name"]
        permissions = (
            ("run_syncjob", "Kann Synchronisationsjobs ausführen"),
            ("test_syncjob", "Kann Synchronisationsjobs testen"),
            ("garbage_collect_syncjob", "Kann Synchronisationsbereinigung ausführen"),
        )

    def __str__(self):
        return self.name

    def clean(self):
        errors = {}

        if self.scope == self.Scope.ORGANIZATION and self.department_id is not None:
            errors["department"] = "Organisationsweite Jobs dürfen keiner Abteilung zugeordnet sein."

        if self.scope == self.Scope.DEPARTMENT and self.department_id is None:
            errors["department"] = "Abteilungsgebundene Jobs benötigen eine Abteilung."

        if self.run_mode == self.RunMode.INTERVAL:
            if not self.interval_minutes:
                errors["interval_minutes"] = "Intervall-Jobs benötigen eine Intervallangabe."
        elif self.interval_minutes is not None:
            errors["interval_minutes"] = "Ein Intervall ist nur für Intervall-Jobs erlaubt."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.run_mode == self.RunMode.INTERVAL and self.enabled and self.interval_minutes:
            base = self.last_run_at or timezone.now()
            self.next_run_at = base + timezone.timedelta(minutes=self.interval_minutes)
        elif self.run_mode == self.RunMode.MANUAL:
            self.next_run_at = None
        super().save(*args, **kwargs)


class SyncRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ausstehend"
        RUNNING = "running", "Läuft"
        SUCCEEDED = "succeeded", "Erfolgreich"
        FAILED = "failed", "Fehlgeschlagen"
        CANCELLED = "cancelled", "Abgebrochen"

    job = models.ForeignKey(SyncJob, on_delete=models.CASCADE, related_name="runs", verbose_name="Job")
    triggered_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sync_runs",
        verbose_name="Ausgelöst von",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="Status")
    trigger = models.CharField(max_length=30, default="manual", verbose_name="Auslöser")
    summary = models.JSONField(default=dict, blank=True, verbose_name="Zusammenfassung")
    imported_members = models.PositiveIntegerField(default=0, verbose_name="Importierte Mitglieder")
    imported_groups = models.PositiveIntegerField(default=0, verbose_name="Importierte Gruppen")
    updated_members = models.PositiveIntegerField(default=0, verbose_name="Aktualisierte Mitglieder")
    updated_groups = models.PositiveIntegerField(default=0, verbose_name="Aktualisierte Gruppen")
    flagged_for_review = models.PositiveIntegerField(default=0, verbose_name="Zur Prüfung markiert")
    deleted_objects = models.PositiveIntegerField(default=0, verbose_name="Gelöschte Objekte")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Gestartet am")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Beendet am")
    error_message = models.TextField(blank=True, verbose_name="Fehlermeldung")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")

    class Meta:
        verbose_name = "Synchronisationslauf"
        verbose_name_plural = "Synchronisationsläufe"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.job} - {self.get_status_display()}"


class SyncBinding(models.Model):
    class ObjectType(models.TextChoices):
        MEMBER = "member", "Mitglied"
        GROUP = "group", "Gruppe"
        DEPARTMENT = "department", "Abteilung"

    job = models.ForeignKey(SyncJob, on_delete=models.CASCADE, related_name="bindings", verbose_name="Job")
    object_type = models.CharField(max_length=20, choices=ObjectType.choices, verbose_name="Objekttyp")
    external_id = models.CharField(max_length=255, verbose_name="Externe ID")
    external_name = models.CharField(max_length=255, blank=True, verbose_name="Externer Name")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="Inhaltstyp")
    object_id = models.PositiveBigIntegerField(verbose_name="Objekt-ID")
    content_object = GenericForeignKey("content_type", "object_id")
    is_deleted_in_source = models.BooleanField(default=False, verbose_name="In Quelle gelöscht")
    pending_garbage_collection = models.BooleanField(default=False, verbose_name="Zur Bereinigung vorgemerkt")
    override_local_changes = models.BooleanField(default=False, verbose_name="Lokale Änderungen überschreiben")
    managed_fields = models.JSONField(default=list, blank=True, verbose_name="Gesteuerte Felder")
    last_seen_at = models.DateTimeField(null=True, blank=True, verbose_name="Zuletzt gesehen")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "Synchronisationsbindung"
        verbose_name_plural = "Synchronisationsbindungen"
        ordering = ["object_type", "external_name", "external_id"]
        constraints = [
            models.UniqueConstraint(fields=["job", "object_type", "external_id"], name="uniq_sync_binding_ext"),
            models.UniqueConstraint(
                fields=["job", "content_type", "object_id"],
                name="uniq_sync_binding_object",
            ),
        ]

    def __str__(self):
        return f"{self.get_object_type_display()}: {self.external_name or self.external_id}"
