from django.db import models
from django.urls import reverse
from .member import Member

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

    def get_full_name(self):
        """Gibt den vollständigen Namen des Elternteils zurück"""
        return f"{self.name} {self.lastname}".strip()

    def get_whatsapp_number(self):
        number = self.mobile.replace(' ','').replace('+','')
        return number

    def get_absolute_url(self):
        return reverse('members:parent_edit', kwargs={'pk': self.pk})
