from django.db import models
from django.core.exceptions import ValidationError
from members.models.member import Member


class StorageLocation(models.Model):
    """Lagerort mit hierarchischer Struktur"""
    name = models.CharField(max_length=200, verbose_name='Name')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Übergeordneter Lagerort',
        help_text='Übergeordneter Lagerort für hierarchische Struktur'
    )
    is_member = models.BooleanField(
        default=False,
        verbose_name='Ist Mitglied',
        help_text='Markiert diesen Ort als Mitglied-Lagerort'
    )
    member = models.OneToOneField(
        Member,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='personal_storage_location',
        verbose_name='Mitglied',
        help_text='Verknüpftes Mitglied, falls is_member=True'
    )

    class Meta:
        verbose_name = 'Lagerort'
        verbose_name_plural = 'Lagerorte'
        ordering = ['name']

    def __str__(self):
        if self.is_member and self.member:
            return f"{self.name} ({self.member.name} {self.member.lastname})"
        return self.name

    def get_full_path(self):
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name

    def get_level(self):
        if self.parent:
            return self.parent.get_level() + 1
        return 0

    def get_children_recursive(self):
        children = list(self.children.all())
        for child in list(children):
            children.extend(child.get_children_recursive())
        return children

    def clean(self):
        if self.is_member and not self.member:
            raise ValidationError('Wenn "Ist Mitglied" aktiviert ist, muss ein Mitglied ausgewählt werden.')
        if not self.is_member and self.member:
            raise ValidationError('Wenn ein Mitglied ausgewählt ist, muss "Ist Mitglied" aktiviert werden.')
        if self.parent:
            current = self.parent
            while current:
                if current == self:
                    raise ValidationError('Ein Lagerort kann nicht sein eigener Übergeordneter sein.')
                current = current.parent
