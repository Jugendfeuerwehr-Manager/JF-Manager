from datetime import date
from io import BytesIO

from PIL import Image
from colorfield.fields import ColorField
from django.db import models
import uuid, os
# Create your models here.
from django.dispatch import receiver
from django.urls import reverse
from django.core.files import File
import phonenumbers
from django.conf import settings


def get_file_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    return os.path.join(settings.MEDIA_ROOT, '', filename)


class Group(models.Model):

    class Meta:
        verbose_name = "Gruppe"
        verbose_name_plural = "Gruppen"

    name = models.CharField(max_length=200, default='', verbose_name="Gruppenname")

    def __str__(self):
        return self.name


class Status(models.Model):

    class Meta:
        verbose_name = "Status"
        verbose_name_plural = "Status"

    name = models.CharField(max_length=200, default='', verbose_name="Mitgliedschaftsstatus")
    color = ColorField(default='#FF0000')

    def __str__(self):
        return self.name


class Member(models.Model):
    name = models.CharField(max_length=200, default='', verbose_name="Name")
    lastname = models.CharField(max_length=200, default='', verbose_name="Nachname")
    avatar = models.FileField(upload_to=get_file_path,
                        null=True,
                        blank=True,
                        verbose_name='Ausweisbild')
    birthday = models.DateField('Geburtstag', null=True, blank=True)
    email = models.CharField(max_length=200, blank=True, default='', verbose_name='E-Mail')
    street = models.CharField(max_length=200, blank=True, default='', verbose_name='Straße')
    zip_code = models.CharField(max_length=200, blank=True, default='', verbose_name='PLZ')
    city = models.CharField(max_length=200, blank=True, default='', verbose_name='Stadt / Ort')
    phone = models.CharField(max_length=200, blank=True, default='', verbose_name='Telefon')
    mobile = models.CharField(max_length=200, blank=True, default='', verbose_name='Mobil')
    notes = models.TextField(blank=True, default='', verbose_name='Bemerkungen')
    joined = models.DateField('Eingetreten', null=True, blank=True,)
    identityCardNumber = models.CharField(max_length=50, blank=True, default='', verbose_name='Ausweis Nr.')
    canSwimm = models.BooleanField(default=False, verbose_name='Kann schwimmen')
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True)

    def get_absolute_url(self):
        return reverse('members:detail', kwargs={'pk': self.pk})

    def get_age(self):
        if not self.birthday:
            return 0

        born = self.birthday
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def __str__(self):
        return self.name + " " + self.lastname

class Parent(models.Model):
    name = models.CharField(max_length=200, default='', verbose_name="Name")
    lastname = models.CharField(max_length=200, default='', verbose_name="Nachname")
    children = models.ManyToManyField(Member, blank=True, )
    email = models.CharField(max_length=200, blank=True, default='', verbose_name='E-Mail 1')
    email2 = models.CharField(max_length=200, blank=True, default='', verbose_name='E-Mail 2')
    street = models.CharField(max_length=200, blank=True, default='', verbose_name='Straße')
    zip_code = models.CharField(max_length=200, blank=True, default='', verbose_name='PLZ')
    city = models.CharField(max_length=200, blank=True, default='', verbose_name='Stadt / Ort')
    phone = models.CharField(max_length=200, blank=True, default='', verbose_name='Telefon')
    mobile = models.CharField(max_length=200, blank=True, default='', verbose_name='Mobil')
    notes = models.TextField(blank=True, default='', verbose_name='Bemerkungen')

    def __str__(self):
        return self.name + " " + self.lastname

    def get_whatsapp_number(self):
        number = self.mobile.replace(' ','').replace('+','')
        return number


    def get_absolute_url(self):
        return reverse('members:parent_edit', kwargs={'pk': self.pk})


class EventType(models.Model):
    name = models.CharField(max_length=200, default='', verbose_name="Ereignistyp")

    def __str__(self):
        return self.name

class Event(models.Model):
    type = models.ForeignKey(EventType, on_delete=models.CASCADE, null=True)
    datetime = models.DateField(verbose_name="Datum", null=False, blank=False)
    notes = models.TextField(blank=True, default='', verbose_name='Bemerkungen')
    member = models.ForeignKey(Member, blank=False, null=True, on_delete=models.CASCADE)
