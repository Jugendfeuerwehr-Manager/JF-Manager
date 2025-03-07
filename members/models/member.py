from datetime import date
from django.db import models
from django.urls import reverse
from .group import Group
from .status import Status
from .utils import get_file_path

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
