"""Effects of changing a service that already has registrations (PART-01.5, concept 4.5 and 6.3).

Registrations are never deleted. A new date or time keeps all of them; derived deadlines follow the
start by themselves (``service.deadlines``) and explicit ones are capped at the new start.
"""

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from members.models import Member
from training.models import TrainingSession

from .models import Mode, Registration, RegistrationEvent, SessionParticipation

ACTIVE = (
    Registration.State.REGISTERED,
    Registration.State.WAITLISTED,
    Registration.State.APPLIED,
    Registration.State.ASSIGNED,
)
TRACKED = ("status", "date", "start_time", "end_time", "location")


def snapshot_values(session):
    """Normalised tracked values (strings given by raw API input are converted)."""
    out = {}
    for name in TRACKED:
        value = getattr(session, name)
        out[name] = value if name in ("status", "location") else TrainingSession._meta.get_field(name).to_python(value)
    return out


def cap_explicit_deadlines(session):
    """Explicit deadlines later than the (new) start are pulled back to the start."""
    from .service import session_start

    start = session_start(session)
    for name in ("registration_opens_at", "registration_closes_at", "cancellation_closes_at"):
        SessionParticipation.objects.filter(session=session, **{f"{name}__gt": start}).update(
            **{name: start, "revision": F("revision") + 1}
        )


def target_member_ids(session):
    members = Member.objects.none()
    group_ids = list(session.groups.values_list("pk", flat=True))
    if group_ids:
        members = Member.objects.filter(group_id__in=group_ids)
    elif session.department_id:
        members = Member.objects.filter(departments=session.department_id)
    return set(members.values_list("pk", flat=True))


def affected_member_ids(session, mode):
    registrations = Registration.objects.filter(session=session)
    ids = set(registrations.filter(state__in=ACTIVE).values_list("member_id", flat=True))
    if mode == Mode.OPT_OUT:
        cancelled = set(registrations.filter(state=Registration.State.CANCELLED).values_list("member_id", flat=True))
        ids |= target_member_ids(session) - cancelled
    return sorted(ids)


def apply_mode_change(session, previous_mode, participation, *, now=None):
    """Bring existing registrations in line after the mode of a service changed. Returns changed rows.

    * to opt-out: everybody is expected, so waitlisted/applied/assigned/not-selected people become
      ``registered`` ("confirmed"); cancellations stay cancelled; the caller drops the maximum (D5).
    * opt-out -> opt-in/assignment: nothing changes; cancellations stay, "expected" people without a row
      become "no response", people with a ``registered`` row (a taken-back cancellation) stay registered.
    * assignment -> opt-in: applied/assigned people become registered, or waitlisted once the maximum
      is reached (oldest first); not-selected stays.
    * opt-in -> assignment: waitlisted people become applied.
    The caller holds the session lock. History is kept: every change writes a ``system`` event.
    """
    mode = participation.mode
    if mode == previous_mode:
        return []
    now = now or timezone.now()
    S = Registration.State
    rows = list(Registration.objects.select_for_update().filter(session=session).order_by("state_changed_at", "pk"))
    if mode == Mode.OPT_OUT:
        plan = {S.WAITLISTED: S.REGISTERED, S.APPLIED: S.REGISTERED, S.ASSIGNED: S.REGISTERED}
        plan[S.NOT_SELECTED] = S.REGISTERED
    elif mode == Mode.ASSIGNMENT:
        plan = {S.WAITLISTED: S.APPLIED}
    else:  # opt_in
        plan = {S.APPLIED: S.REGISTERED, S.ASSIGNED: S.REGISTERED}
    seated = sum(r.state in (S.REGISTERED, S.ASSIGNED) for r in rows)
    changed = []
    with transaction.atomic():
        for row in rows:
            target = plan.get(row.state)
            if target is None:
                continue
            if mode == Mode.OPT_IN and target == S.REGISTERED:
                limit = participation.max_participants
                if row.state == S.APPLIED and limit is not None and seated >= limit:
                    target = S.WAITLISTED
                elif row.state == S.APPLIED:
                    seated += 1
            previous = row.state
            row.state, row.state_changed_at = target, now
            row.version += 1
            row.save(update_fields=["state", "state_changed_at", "version", "updated_at"])
            RegistrationEvent.objects.create(
                registration=row, actor=None, from_state=previous, to_state=target, at=now, via="system"
            )
            changed.append(row)
    return changed
