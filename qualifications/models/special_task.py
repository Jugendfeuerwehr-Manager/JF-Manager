from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericRelation
from datetime import date


class SpecialTaskType(models.Model):
    """
    Typ einer Sonderaufgabe (z.B. Jugendsprecher, Kleiderwart)
    """
    class Meta:
        verbose_name = "Sonderaufgaben-Typ"
        verbose_name_plural = "Sonderaufgaben-Typen"
        ordering = ['name']

    name = models.CharField(
        max_length=200,
        verbose_name="Name",
        help_text="z.B. 'Jugendsprecher', 'Kleiderwart'"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Beschreibung"
    )

    def __str__(self):
        return self.name


class SpecialTask(models.Model):
    """
    Eine Sonderaufgabe einer Person
    """
    class Meta:
        verbose_name = "Sonderaufgabe"
        verbose_name_plural = "Sonderaufgaben"
        ordering = ['-start_date']
        permissions = [
            ('view_all_specialtasks', 'Kann alle Sonderaufgaben einsehen'),
            ('manage_specialtasks', 'Kann Sonderaufgaben verwalten'),
        ]

    task = models.ForeignKey(
        SpecialTaskType,
        on_delete=models.CASCADE,
        verbose_name="Aufgabe"
    )
    
    # Sowohl CustomUser als auch Member können Sonderaufgaben haben
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Benutzer",
        related_name='special_tasks'
    )
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Mitglied",
        related_name='special_tasks'
    )
    
    start_date = models.DateField(
        verbose_name="Startdatum",
        help_text="Datum des Beginns der Aufgabe"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Enddatum",
        help_text="Datum des Endes der Aufgabe (leer = noch aktiv)"
    )
    note = models.TextField(
        blank=True,
        verbose_name="Notiz"
    )
    
    # Generic relation to attachments
    attachments = GenericRelation(
        'members.Attachment',
        related_query_name='specialtask'
    )

    def __str__(self):
        person = self.get_person_name()
        status = "aktiv" if self.is_active() else "beendet"
        return f"{person} - {self.task.name} ({status})"

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

    def is_active(self):
        """Prüft, ob die Aufgabe noch aktiv ist"""
        return self.end_date is None or self.end_date > date.today()

    def get_status_class(self):
        """Gibt CSS-Klasse für Status zurück"""
        if self.is_active():
            return 'table-success'
        return 'table-secondary'

    def get_duration_days(self):
        """Berechnet die Dauer der Aufgabe in Tagen"""
        end = self.end_date or date.today()
        return (end - self.start_date).days

    def clean(self):
        # Mindestens User oder Member muss gesetzt sein
        if not self.user and not self.member:
            raise ValidationError('Entweder Benutzer oder Mitglied muss ausgewählt werden.')
        
        # Nicht beide gleichzeitig
        if self.user and self.member:
            raise ValidationError('Nur Benutzer oder Mitglied kann ausgewählt werden, nicht beide.')
        
        # Enddatum nicht vor Startdatum
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'Enddatum kann nicht vor Startdatum liegen.'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
