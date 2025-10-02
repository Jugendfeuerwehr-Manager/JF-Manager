from django.db import models
from .member import Member

class EventType(models.Model):
    name = models.CharField(max_length=200, default='', verbose_name="Ereignistyp")

    def __str__(self):
        return self.name

class Event(models.Model):
    type = models.ForeignKey(EventType, on_delete=models.CASCADE, null=True)
    datetime = models.DateField(verbose_name="Datum", null=False, blank=False)
    notes = models.TextField(blank=True, default='', verbose_name='Bemerkungen')
    member = models.ForeignKey(Member, blank=False, null=True, on_delete=models.CASCADE)
