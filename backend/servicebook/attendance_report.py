"""Attendance evaluation per period for members and team: rates, hours, monthly course, trend and warnings."""

from datetime import date

from django.utils import timezone

from members.models import Member
from servicebook.models import Attendance, StaffAttendance
from users.people import person_accounts

# Warning thresholds; rates are fractions of recorded entries (present, excused, absent).
LOW_RATE = 0.5
LOW_RATE_MIN_RECORDS = 4
DECLINE_POINTS = 25
DECLINE_MIN_RECORDS_PER_HALF = 4
MISSED_STREAK = 3

STATE_KEYS = {"A": "present", "E": "excused", "F": "absent"}


def default_period(today: date | None = None) -> tuple[date, date]:
    """The last twelve months including the current one."""
    today = today or timezone.localdate()
    year, month = today.year, today.month - 11
    if month < 1:
        year, month = year - 1, month + 12
    return date(year, month, 1), today


def month_keys(date_from: date, date_to: date) -> list[str]:
    keys = []
    year, month = date_from.year, date_from.month
    while (year, month) <= (date_to.year, date_to.month):
        keys.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return keys


def _rate(present: int, recorded: int) -> float | None:
    return round(100 * present / recorded, 1) if recorded else None


def _counts() -> dict:
    return {"present": 0, "excused": 0, "absent": 0, "recorded": 0}


def _add(counts: dict, state: str) -> None:
    counts[STATE_KEYS[state]] += 1
    counts["recorded"] += 1


def _person_row(person_id, full_name, records, months) -> dict:
    """Evaluate one person's records, given as (start, hours, month, state) sorted by start."""
    counts = _counts()
    hours = 0.0
    per_month = {key: _counts() for key in months}
    # Trend compares the person's earlier and later half of entries, not calendar halves,
    # so someone with few early entries is not judged on them alone.
    previous, recent = _counts(), _counts()
    half = len(records) // 2
    for index, (_start, service_hours, month, state) in enumerate(records):
        _add(counts, state)
        _add(per_month[month], state)
        _add(previous if index < half else recent, state)
        if state == "A":
            hours += service_hours

    streak = 0
    for *_, state in reversed(records):
        if state == "A":
            break
        streak += 1

    rate = _rate(counts["present"], counts["recorded"])
    trend = None
    if previous["recorded"] >= DECLINE_MIN_RECORDS_PER_HALF and recent["recorded"] >= DECLINE_MIN_RECORDS_PER_HALF:
        previous_rate = _rate(previous["present"], previous["recorded"])
        recent_rate = _rate(recent["present"], recent["recorded"])
        trend = {"previous": previous_rate, "recent": recent_rate, "delta": round(recent_rate - previous_rate, 1)}

    warnings = []
    if counts["recorded"] >= LOW_RATE_MIN_RECORDS and counts["present"] < LOW_RATE * counts["recorded"]:
        warnings.append("low_rate")
    if trend and trend["delta"] <= -DECLINE_POINTS:
        warnings.append("declining")
    if streak >= MISSED_STREAK:
        warnings.append("missed_in_a_row")

    return {
        "id": person_id,
        "full_name": full_name,
        **counts,
        "rate": rate,
        "hours": round(hours, 2),
        "months": [_rate(per_month[key]["present"], per_month[key]["recorded"]) for key in months],
        "trend": trend,
        "missed_in_a_row": streak,
        "warnings": warnings,
    }


def _group_report(rows, months, names, service_info) -> dict:
    """Aggregate (person_id, service_id, state) rows into per-person results and a group summary."""
    records_by_person = {}
    month_totals = {key: _counts() for key in months}
    totals = _counts()
    for person_id, service_id, state in rows:
        if state not in STATE_KEYS or person_id not in names:
            continue
        start, service_hours, month = service_info[service_id]
        records_by_person.setdefault(person_id, []).append((start, service_hours, month, state))
        _add(month_totals[month], state)
        _add(totals, state)

    people = []
    for person_id, records in records_by_person.items():
        records.sort(key=lambda record: record[0])
        people.append(_person_row(person_id, names[person_id], records, months))
    order = {person_id: index for index, person_id in enumerate(names)}
    people.sort(key=lambda row: order[row["id"]])

    return {
        "summary": {
            **totals,
            "rate": _rate(totals["present"], totals["recorded"]),
            "people": len(people),
            "with_warnings": sum(1 for row in people if row["warnings"]),
        },
        "months": [
            {
                "month": key,
                **month_totals[key],
                "rate": _rate(month_totals[key]["present"], month_totals[key]["recorded"]),
            }
            for key in months
        ],
        "people": people,
    }


def attendance_report(services, date_from: date, date_to: date) -> dict:
    """Build the evaluation for already permission-scoped services within the period."""
    services = services.filter(start__date__gte=date_from, start__date__lte=date_to)
    months = month_keys(date_from, date_to)

    service_info = {}
    total_hours = 0.0
    for service_id, start, end in services.values_list("pk", "start", "end"):
        local_start = timezone.localtime(start)
        service_hours = max(0.0, (end - start).total_seconds() / 3600)
        service_info[service_id] = (local_start, service_hours, local_start.strftime("%Y-%m"))
        total_hours += service_hours

    member_rows = list(
        Attendance.objects.filter(service_id__in=service_info).values_list("person_id", "service_id", "state")
    )
    staff_rows = list(
        StaffAttendance.objects.filter(service_id__in=service_info).values_list("person_id", "service_id", "state")
    )
    # Names in display order; inactive accounts keep their history, the system account never appears.
    member_names = {
        member.pk: member.get_full_name()
        for member in Member.objects.filter(pk__in={row[0] for row in member_rows}).order_by("lastname", "name")
    }
    staff_names = {
        user.pk: user.get_full_name() or user.username
        for user in person_accounts(active_only=False)
        .filter(pk__in={row[0] for row in staff_rows})
        .order_by("last_name", "first_name", "username")
    }

    return {
        "period": {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
        "services": {"count": len(service_info), "hours": round(total_hours, 2)},
        "thresholds": {
            "low_rate": round(LOW_RATE * 100),
            "low_rate_min_records": LOW_RATE_MIN_RECORDS,
            "decline_points": DECLINE_POINTS,
            "missed_in_a_row": MISSED_STREAK,
        },
        "members": _group_report(member_rows, months, member_names, service_info),
        "staff": _group_report(staff_rows, months, staff_names, service_info),
    }
