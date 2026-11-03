"""DJF annual report (Jahresmeldung) of one department, in the order of the DJF statistics portal.

Members are counted at the reference date (31.12.) from join dates, leave dates and the
department's movements; anonymized former members still count (gender, birth year and the
dates are kept). Ages of anonymized members are approximated from the birth year.
"""

from collections import defaultdict
from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from members.models import Member, Status
from membership.models import AnnualReport, MembershipEvent, StatisticsProfile

Kind = MembershipEvent.Kind
GENDERS = {"male": "m", "female": "w", "diverse": "d"}
AGE_ROWS = (
    [("lt5", "unter 5 Jahre")] + [(str(age), f"{age} Jahre") for age in range(5, 19)] + [("gt18", "über 18 Jahre")]
)
MOVEMENT_ROWS = [
    ("joined_new", "Zugang neu"),
    ("joined_other_org", "Zugang andere Organisation"),
    ("joined_from_kf", "Zugang aus Kinderfeuerwehr"),
    ("exit_ea", "Abgang in die Einsatzabteilung"),
    ("exit_other", "Abgang sonstige"),
]
JOINS = ("joined_new", "joined_other_org", "joined_from_kf")
EXITS = ("exit_ea", "exit_other")
SUBJECT = "membership.annualreport"


def _counter():
    return {"m": 0, "w": 0, "d": 0, "total": 0}


def _add(counter, gender):
    counter[gender] += 1
    counter["total"] += 1


def _age_key(member, day):
    if member.birthday is None:
        return None
    if member.anonymized_at is not None:
        age = day.year - member.birthday.year  # only the birth year is kept
    else:
        age = day.year - member.birthday.year - ((day.month, day.day) < (member.birthday.month, member.birthday.day))
    if age < 5:
        return "lt5"
    if age > 18:
        return "gt18"
    return str(age)


def _label(member):
    if member.anonymized_at is not None:
        return f"Ehemaliges Mitglied #{member.pk}"
    return f"{member.name} {member.lastname}".strip()


class _Periods:
    """When each member belonged to the department: (entry, exit) from movements and dates."""

    def __init__(self, department, profile):
        excluded = {Status.Category.APPLICANT}
        if "passive" not in profile.include_status_categories:
            excluded.add(Status.Category.PASSIVE)
        events = defaultdict(list)
        for event in MembershipEvent.objects.filter(department=department).order_by("date", "pk"):
            events[event.member_id].append(event)
        linked = set(Member.objects.filter(departments=department).values_list("pk", flat=True))
        self.members = list(
            Member.objects.filter(pk__in=linked | set(events))
            .exclude(status__category__in=excluded)
            .select_related("status")
        )
        self.events = events
        self.linked = linked

    def entry(self, member):
        joins = [event.date for event in self.events[member.pk] if event.kind in JOINS]
        return min(joins) if joins else member.joined

    def exit(self, member):
        if member.left_at is not None:
            return member.left_at
        if member.pk in self.linked:
            return None
        exits = [event.date for event in self.events[member.pk] if event.kind in EXITS]
        return max(exits) if exits else None

    def in_stock(self, member, day):
        entry, leaving = self.entry(member), self.exit(member)
        return entry is not None and entry <= day and (leaving is None or leaving > day)


def _stock(periods, day, warnings=None):
    totals, ages, approximated = _counter(), {key: _counter() for key, _ in AGE_ROWS}, 0
    for member in periods.members:
        if not periods.in_stock(member, day):
            continue
        gender = GENDERS.get(member.gender)
        age_key = _age_key(member, day)
        if warnings is not None and gender is None:
            warnings.append({"member": member.pk, "name": _label(member), "message": "Geschlecht fehlt"})
        if warnings is not None and age_key is None:
            warnings.append({"member": member.pk, "name": _label(member), "message": "Geburtsdatum fehlt"})
        if gender is None:
            continue
        _add(totals, gender)
        if age_key is not None:
            _add(ages[age_key], gender)
        approximated += member.anonymized_at is not None
    return totals, ages, approximated


def _movements(periods, year, warnings):
    """Movements of the year. Join or leave dates without a recorded movement (older data, the
    leave date edited in the member form) count as "neu" or "sonstige" so stock and movements agree.
    """
    rows = {key: _counter() for key, _ in MOVEMENT_ROWS}
    reasons = {value: 0 for value, _ in MembershipEvent.ExitReason.choices}
    for member in periods.members:
        gender = GENDERS.get(member.gender)
        if gender is None:
            continue
        events = periods.events[member.pk]
        for event in events:
            if event.date.year != year or event.kind not in rows:
                continue
            _add(rows[event.kind], gender)
            if event.kind != Kind.EXIT_OTHER:
                continue
            if event.exit_reason:
                reasons[event.exit_reason] += 1
            else:
                warnings.append({"member": member.pk, "name": _label(member), "message": "Abgang ohne Grund"})
        _implicit(member, events, periods, year, gender, rows, warnings)
    return rows, reasons


def _implicit(member, events, periods, year, gender, rows, warnings):
    entry, leaving = periods.entry(member), periods.exit(member)
    has_join = any(event.kind in JOINS for event in events)
    if not has_join and entry is not None and entry.year == year:
        _add(rows["joined_new"], gender)
        warnings.append(
            {"member": member.pk, "name": _label(member), "message": "Eintritt ohne Zugangsart (als „neu“ gezählt)"}
        )
    has_exit = any(event.kind in EXITS and event.date == leaving for event in events)
    if not has_exit and leaving is not None and leaving.year == year:
        _add(rows["exit_other"], gender)
        warnings.append({"member": member.pk, "name": _label(member), "message": "Austritt ohne Abgangsart und Grund"})


def _previous(department, year, periods):
    snapshot = AnnualReport.objects.filter(department=department, year=year - 1, state=AnnualReport.State.FINAL).first()
    if snapshot is not None:
        return {**snapshot.data["members"], "source": "snapshot"}
    totals, _, _ = _stock(periods, date(year - 1, 12, 31))
    return {**totals, "source": "computed"}


def _checks(members, previous, movements, ages, reasons):
    checks = []
    for gender, label in (("m", "männlichen"), ("w", "weiblichen"), ("d", "diversen")):
        age_sum = sum(row[gender] for row in ages.values())
        checks.append(
            {
                "rule": f"age_{gender}",
                "ok": age_sum == members[gender],
                "message": f"Die Anzahl der {label} Mitglieder ({members[gender]}) entspricht der Summe der Altersstruktur ({age_sum}).",
            }
        )
        expected = (
            previous[gender]
            + sum(movements[key][gender] for key in JOINS)
            - sum(movements[key][gender] for key in EXITS)
        )
        checks.append(
            {
                "rule": f"balance_{gender}",
                "ok": expected == members[gender],
                "message": f"Vorjahr + Zugänge − Abgänge ({expected}) ergibt die {label} Mitglieder ({members[gender]}).",
            }
        )
    reason_sum = sum(reasons.values())
    checks.append(
        {
            "rule": "reasons",
            "ok": reason_sum == movements["exit_other"]["total"],
            "message": f"Die Gründe ({reason_sum}) ergeben die sonstigen Abgänge ({movements['exit_other']['total']}).",
        }
    )
    return checks


def compute(department, year):
    """The report numbers for ``department`` and ``year`` (not stored)."""
    profile, _ = StatisticsProfile.objects.get_or_create(department=department)
    reference = date(year, 12, 31)
    periods = _Periods(department, profile)
    warnings = []
    members, ages, approximated = _stock(periods, reference, warnings)
    movements, reasons = _movements(periods, year, warnings)
    previous = _previous(department, year, periods)
    checks = _checks(members, previous, movements, ages, reasons)
    return {
        "year": year,
        "reference_date": reference.isoformat(),
        "organisation": {
            "name": department.name,
            "djf_org_id": profile.djf_org_id,
            "org_kind": profile.org_kind,
            "founded_on": profile.founded_on.isoformat() if profile.founded_on else None,
        },
        "members": members,
        "previous": previous,
        "movements": [{"key": key, "label": label, **movements[key]} for key, label in MOVEMENT_ROWS],
        "exit_reasons": [
            {"key": value, "label": label, "total": reasons[value]}
            for value, label in MembershipEvent.ExitReason.choices
        ],
        "age": [{"key": key, "label": label, **ages[key]} for key, label in AGE_ROWS],
        "checks": checks,
        "ok": all(check["ok"] for check in checks),
        "warnings": warnings,
        "approximated_ages": approximated,
        "suggestions": _suggestions(department, year),
    }


def _suggestions(department, year):
    from departments.models import UserDepartmentRole
    from servicebook.models import Service

    return {
        "supervisors": UserDepartmentRole.objects.filter(department=department).values("user").distinct().count(),
        "services": Service.objects.filter(department=department, start__year=year).count(),
    }


def report_for(department, year):
    """The stored report if final, otherwise freshly computed with the saved manual values."""
    report = AnnualReport.objects.filter(department=department, year=year).first()
    if report is not None and report.state == AnnualReport.State.FINAL:
        return report, report.data
    data = compute(department, year)
    data["manual"] = report.manual if report else {}
    return report, data


def save_manual(department, year, manual):
    report, _ = AnnualReport.objects.get_or_create(
        department=department, year=year, defaults={"reference_date": date(year, 12, 31)}
    )
    if report.state == AnnualReport.State.FINAL:
        raise ValidationError({"detail": "Die Jahresmeldung ist festgeschrieben."})
    report.manual = manual
    report.save(update_fields=["manual", "updated_at"])
    return report


def finalize(department, year, *, by=None):
    """Freeze and seal the numbers; later corrections of members no longer change this year."""
    from admissions.models import Seal
    from admissions.services import seal as seal_service

    with transaction.atomic():
        report, _ = AnnualReport.objects.select_for_update().get_or_create(
            department=department, year=year, defaults={"reference_date": date(year, 12, 31)}
        )
        if report.state == AnnualReport.State.FINAL:
            raise ValidationError({"detail": "Die Jahresmeldung ist bereits festgeschrieben."})
        if date(year, 12, 31) >= timezone.localdate():
            raise ValidationError({"detail": "Festschreiben ist erst nach dem Stichtag möglich."})
        data = compute(department, year)
        data["manual"] = report.manual
        report.data = data
        report.state = AnnualReport.State.FINAL
        report.finalized_at = timezone.now()
        report.finalized_by = by
        report.save()
        seal_service.seal(subject_type=SUBJECT, subject_id=report.pk, kind=Seal.Kind.ANNUAL_REPORT, content=data)
    return report
