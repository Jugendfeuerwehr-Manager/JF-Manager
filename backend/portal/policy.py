"""Portal data release (PORTAL-02, concept 4.2 / E7 / D2 / D3).

The organisation sets defaults and a ceiling (allowed/locked) per category and
audience; departments restrict or release within it. Notes, events,
attachments, attendance and statistics are no category: they are never
serialised for portal accounts.
"""

from dataclasses import dataclass, field

from django.utils import timezone

from .models import PortalPolicy

AUDIENCES = ("parents", "members")
VISIBLE, HIDDEN = "visible", "hidden"
ALLOWED, LOCKED = "allowed", "locked"

# key: (label, hint, default for parents, default for members, fixed)
# A default of None means the category does not exist for that audience.
CATEGORIES = {
    "contact": ("Name und Kontakt", "Immer sichtbar, Grundlage für Anträge", VISIBLE, VISIBLE, True),
    "birthday": ("Geburtsdatum", "Nur lesbar", VISIBLE, VISIBLE, False),
    "group": ("Gruppe und Abteilung", "", VISIBLE, VISIBLE, False),
    "membership": ("Mitgliedsstatus und Eintritt", "", HIDDEN, HIDDEN, False),
    "identity": ("Ausweisnummer und Ausweisbild", "", HIDDEN, HIDDEN, False),
    "swimming": ("Schwimmfähigkeit", "", HIDDEN, HIDDEN, False),
    "qualifications": ("Qualifikationen", "Art, erworben, gültig bis · ohne Notizen", VISIBLE, VISIBLE, False),
    "special_tasks": ("Sonderaufgaben", "Aufgabe und Zeitraum · ohne Notizen", HIDDEN, HIDDEN, False),
    "equipment": ("Ausgegebene Ausrüstung", "Artikel, Variante, Menge", HIDDEN, HIDDEN, False),
    "other_parents": ("Weitere Kontaktpersonen des Kindes", "Name und Telefon", HIDDEN, None, False),
    "registrations": ("Meldehistorie", "Eigene An- und Abmeldungen, keine Anwesenheit", VISIBLE, VISIBLE, True),
}
NEVER_VISIBLE = (
    "Bemerkungen, Mitgliederereignisse, Anhänge, Anwesenheit und Abwesenheit, besondere Vorkommnisse, "
    "Statistiken und Namen anderer Teilnehmender."
)
MEMBER_PORTAL_MODES = ("off", "min_age", "all")


def default_for(category, audience):
    _label, _hint, parents, members, _fixed = CATEGORIES[category]
    return parents if audience == "parents" else members


def applies(category, audience):
    return default_for(category, audience) is not None


def is_fixed(category):
    return CATEGORIES[category][4]


def age_on(birthday, day):
    return day.year - birthday.year - ((day.month, day.day) < (birthday.month, birthday.day))


@dataclass
class PolicySet:
    """All policies loaded once; answers effective questions without further queries."""

    org: PortalPolicy | None
    departments: dict = field(default_factory=dict)

    @classmethod
    def load(cls):
        policies = list(PortalPolicy.objects.all())
        org = next((p for p in policies if p.department_id is None), None)
        return cls(org=org, departments={p.department_id: p for p in policies if p.department_id is not None})

    # ---------------------------------------------------------------- visibility
    def locked(self, category, audience):
        if is_fixed(category):
            return False
        return bool(self.org and self.org.ceiling.get(category, {}).get(audience) == LOCKED)

    def org_value(self, category, audience):
        if not applies(category, audience):
            return None
        if is_fixed(category):
            return VISIBLE
        if self.locked(category, audience):
            return HIDDEN
        value = self.org.visibility.get(category, {}).get(audience) if self.org else None
        return value if value in (VISIBLE, HIDDEN) else default_for(category, audience)

    def department_value(self, department_id, category, audience):
        """Effective value in one department; None if the category does not exist for the audience."""
        base = self.org_value(category, audience)
        if base is None or is_fixed(category) or self.locked(category, audience):
            return base
        policy = self.departments.get(department_id)
        value = policy.visibility.get(category, {}).get(audience) if policy else None
        return value if value in (VISIBLE, HIDDEN) else base

    def visible(self, category, audience, department_ids):
        """Person-level data: visible if visible in at least one department of the person (concept 4.2)."""
        if not applies(category, audience):
            return False
        department_ids = list(department_ids)
        if not department_ids:
            return self.org_value(category, audience) == VISIBLE
        return any(self.department_value(d, category, audience) == VISIBLE for d in department_ids)

    def visible_categories(self, audience, department_ids):
        return [key for key in CATEGORIES if self.visible(key, audience, department_ids)]

    # ---------------------------------------------------------------- member portal (D2/D3)
    def member_mode(self, department_id):
        policy = self.departments.get(department_id)
        mode = policy.member_portal_mode if policy and policy.member_portal_mode else None
        min_age = policy.member_portal_min_age if policy and policy.member_portal_mode else None
        if mode is None:
            mode = self.org.member_portal_mode if self.org and self.org.member_portal_mode else "off"
            min_age = self.org.member_portal_min_age if self.org else None
        return mode, min_age

    def member_allowed(self, member, department_ids, today=None):
        today = today or timezone.localdate()
        for department_id in department_ids:
            mode, min_age = self.member_mode(department_id)
            if mode == "all":
                return True
            if (
                mode == "min_age"
                and min_age is not None
                and member.birthday
                and age_on(member.birthday, today) >= min_age
            ):
                return True
        return False


def member_portal_allowed(member, today=None):
    """D2: allowed if at least one of the member's departments allows the member portal for the age."""
    return PolicySet.load().member_allowed(member, member.departments.values_list("pk", flat=True), today)
