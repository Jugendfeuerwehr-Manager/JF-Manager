from django.db import models
from django.urls import reverse

from members.models import Member

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return self.name

class Item(models.Model):
    size = models.CharField(max_length=100, blank=True, default='', verbose_name='Größe ')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name='Kategorie')
    identifier1 = models.CharField(max_length=255, blank=True, default='', verbose_name='Inventarnummer Hand')
    identifier2 = models.CharField(max_length=255, blank=True, default='', verbose_name='Inventarnummer Barcode')
    rented_by = models.ForeignKey(Member, blank=True, on_delete=models.SET_NULL, null=True, verbose_name='Ausgeliehen von')

    def __str__(self):
        return self.category.name + " gr. " + self.size

    def get_absolute_url(self):
        return reverse('inventory:item_edit', kwargs={'pk': self.pk})

    class Meta:
        permissions = (
            ("can_rent", "can rent items to members"),
        )

