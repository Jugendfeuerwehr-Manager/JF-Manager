from django.db import models

# Create your models here.
from django.urls import reverse

from members.models import Member
from users.models import CustomUser


class Service(models.Model):
    start = models.DateTimeField(verbose_name="Start", null=False, blank=False)
    end = models.DateTimeField(verbose_name="Ende", null=False, blank=False)
    place = models.CharField(verbose_name="Ort", null=True, blank=True, max_length=255)
    operations_manager = models.ManyToManyField(CustomUser, blank=True, verbose_name="Übungsleitung")
    topic = models.CharField(verbose_name="Thema", null=True, blank=True, max_length=255)
    description = models.TextField(verbose_name="Beschreibung", null=True, blank=True)
    events = models.TextField(verbose_name="Besondere Vorkommnisse", null=True, blank=True)
    attendees = models.ManyToManyField(Member, through="Attendance")
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Abteilung",
        related_name="services",
    )
    training_session = models.OneToOneField(
        "training.TrainingSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="servicebook_entry",
        verbose_name="Verknüpfte Ausbildungseinheit",
    )

    def has_events(self):
        return bool(self.events and len(self.events) > 0)

    def get_absolute_url(self):
        return reverse("servicebook:edit", kwargs={"pk": self.pk})

    def __str__(self):
        return f"{self.topic} am {self.start.date().__str__()}"


class Attendance(models.Model):
    STATES = (
        ("A", "Anwesend"),
        ("E", "Entschuldigt"),
        ("F", "Fehlend"),
    )
    person = models.ForeignKey(Member, on_delete=models.CASCADE, null=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True)
    state = models.CharField(max_length=1, choices=STATES, null=True)

    class Meta:
        unique_together = [["person", "service"]]
        indexes = [
            models.Index(fields=["person", "service"]),
        ]

    def __str__(self):
        return f"{self.person.name} war {self.state} bei {self.service.__str__()}"
        # return self.person.name + " war " + self.state + " bei " + self.service.__str__()
