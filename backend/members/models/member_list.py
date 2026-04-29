from django.db import models
from django.utils import timezone


class MemberList(models.Model):
    """
    A named list of members. Members can belong to multiple lists (unlike Group).
    Designed for checklists, event participation, excursions, etc.
    """

    name = models.CharField(max_length=200, verbose_name="Listenname")
    description = models.TextField(blank=True, default='', verbose_name="Beschreibung")
    color = models.CharField(max_length=7, default='#3B82F6', verbose_name="Farbe")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mitgliederliste"
        verbose_name_plural = "Mitgliederlisten"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.entries.count()

    @property
    def checked_count(self):
        return self.entries.filter(checked=True).count()


class MemberListEntry(models.Model):
    """
    Through-table connecting a Member to a MemberList with optional check state and notes.
    """
    member_list = models.ForeignKey(
        MemberList,
        on_delete=models.CASCADE,
        related_name='entries',
        verbose_name="Liste",
    )
    member = models.ForeignKey(
        'Member',
        on_delete=models.CASCADE,
        related_name='list_entries',
        verbose_name="Mitglied",
    )
    checked = models.BooleanField(default=False, verbose_name="Abgehakt")
    checked_at = models.DateTimeField(null=True, blank=True, verbose_name="Abgehakt am")
    notes = models.CharField(max_length=500, blank=True, default='', verbose_name="Notiz")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Listeneintrag"
        verbose_name_plural = "Listeneinträge"
        unique_together = [('member_list', 'member')]
        ordering = ['member__lastname', 'member__name']

    def __str__(self):
        return f"{self.member_list.name} – {self.member}"

    def toggle_check(self):
        self.checked = not self.checked
        self.checked_at = timezone.now() if self.checked else None
        self.save(update_fields=['checked', 'checked_at'])
