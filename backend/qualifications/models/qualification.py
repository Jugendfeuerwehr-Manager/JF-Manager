from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericRelation
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class QualificationType(models.Model):
    """
    Typ einer Qualifikation (z.B. Grundlehrgang, Sprechfunk)
    """
    class Meta:
        verbose_name = "Qualifikationstyp"
        verbose_name_plural = "Qualifikationstypen"
        ordering = ['name']

    name = models.CharField(
        max_length=200, 
        verbose_name="Name",
        help_text="z.B. 'Grundlehrgang', 'Sprechfunk'"
    )
    expires = models.BooleanField(
        default=False,
        verbose_name="Läuft ab",
        help_text="Wenn aktiviert, ist ein Ablaufdatum erforderlich"
    )
    validity_period = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Gültigkeitsdauer (Monate)",
        help_text="Standarddauer in Monaten (nur wenn 'Läuft ab' aktiviert ist)"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Beschreibung"
    )

    def __str__(self):
        return self.name

    def clean(self):
        if self.expires and self.validity_period is None:
            raise ValidationError({
                'validity_period': 'Bei ablaufenden Qualifikationen muss eine Gültigkeitsdauer angegeben werden.'
            })
        if not self.expires and self.validity_period is not None:
            raise ValidationError({
                'validity_period': 'Gültigkeitsdauer kann nur bei ablaufenden Qualifikationen gesetzt werden.'
            })


class Qualification(models.Model):
    """
    Eine Qualifikation einer Person
    """
    class Meta:
        verbose_name = "Qualifikation"
        verbose_name_plural = "Qualifikationen"
        ordering = ['-date_acquired']
        permissions = [
            ('view_all_qualifications', 'Kann alle Qualifikationen einsehen'),
            ('manage_qualifications', 'Kann Qualifikationen verwalten'),
        ]

    type = models.ForeignKey(
        QualificationType,
        on_delete=models.CASCADE,
        verbose_name="Qualifikationstyp"
    )
    
    # Sowohl CustomUser als auch Member können Qualifikationen haben
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Benutzer",
        related_name='qualifications'
    )
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Mitglied",
        related_name='qualifications'
    )
    
    date_acquired = models.DateField(
        verbose_name="Erworben am",
        help_text="Datum des Erwerbs der Qualifikation"
    )
    date_expires = models.DateField(
        null=True,
        blank=True,
        verbose_name="Läuft ab am",
        help_text="Ablaufdatum (falls erforderlich)"
    )
    issued_by = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Ausgestellt von",
        help_text="Organisation oder Person, die die Qualifikation ausgestellt hat"
    )
    note = models.TextField(
        blank=True,
        verbose_name="Notiz"
    )
    
    # Generic relation to attachments
    attachments = GenericRelation(
        'members.Attachment',
        related_query_name='qualification'
    )

    def __str__(self):
        person = self.get_person_name()
        return f"{person} - {self.type.name}"

    def get_person_name(self):
        """Gibt den Namen der Person zurück (User oder Member)"""
        if self.user:
            return self.user.get_full_name() or self.user.username
        elif self.member:
            return self.member.get_full_name()
        return "Unbekannt"

    def get_person(self):
        """Gibt das Person-Objekt zurück (User oder Member)"""
        return self.user or self.member

    def is_expired(self):
        """Prüft, ob die Qualifikation abgelaufen ist"""
        if not self.date_expires:
            return False
        return self.date_expires < date.today()

    def expires_soon(self, days=30):
        """Prüft, ob die Qualifikation bald abläuft"""
        if not self.date_expires:
            return False
        if self.is_expired():
            return False  # Bereits abgelaufene Qualifikationen sind nicht "bald ablaufend"
        return self.date_expires <= date.today() + timedelta(days=days)

    def get_status_class(self):
        """Gibt CSS-Klasse für Status zurück"""
        if self.is_expired():
            return 'table-danger'
        elif self.expires_soon():
            return 'table-warning'
        return 'table-success'

    def clean(self):
        # Mindestens User oder Member muss gesetzt sein
        if not self.user and not self.member:
            raise ValidationError('Entweder Benutzer oder Mitglied muss ausgewählt werden.')
        
        # Nicht beide gleichzeitig
        if self.user and self.member:
            raise ValidationError('Nur Benutzer oder Mitglied kann ausgewählt werden, nicht beide.')
        
        # Automatisches Setzen des Ablaufdatums
        if self.type.expires:
            if not self.date_expires and self.type.validity_period:
                self.date_expires = self.date_acquired + relativedelta(months=self.type.validity_period)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
