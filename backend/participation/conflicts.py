"""Re-check of eligibility for existing registrations (PART-03.5, E11).

Active registrations of upcoming published services are evaluated again against the rule of the
service on its date. A registration that no longer qualifies is flagged (``conflict``); one that
qualifies again is cleared. State and seat are never touched: nobody is de-registered automatically.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from training.models import TrainingSession

from .eligibility import evaluate, load_facts
from .models import Registration, SessionParticipation
from .rules import Names
from .signals import eligibility_conflict

ACTIVE_STATES = (
    Registration.State.REGISTERED,
    Registration.State.WAITLISTED,
    Registration.State.APPLIED,
    Registration.State.ASSIGNED,
)


@dataclass
class RecheckResult:
    conflicted: list = field(default_factory=list)  # newly flagged registration ids
    resolved: list = field(default_factory=list)  # flag cleared again
    checked: int = 0


def recheck(registration_ids=None, member_ids=None, session_ids=None, today=None):
    """Re-evaluate active registrations of upcoming published services; optional filters narrow the scope."""
    today = today or timezone.localdate()
    queryset = Registration.objects.filter(
        state__in=ACTIVE_STATES, session__status=TrainingSession.Status.PUBLISHED, session__date__gte=today
    ).select_related("session")
    if registration_ids is not None:
        queryset = queryset.filter(pk__in=list(registration_ids))
    if member_ids is not None:
        queryset = queryset.filter(member_id__in=list(member_ids))
    if session_ids is not None:
        queryset = queryset.filter(session_id__in=list(session_ids))
    registrations = list(queryset)
    result = RecheckResult(checked=len(registrations))
    if not registrations:
        return result

    rules = {
        sid: rule
        for sid, rule in SessionParticipation.objects.filter(
            session_id__in={r.session_id for r in registrations}
        ).values_list("session_id", "eligibility")
    }
    needed = {r.member_id for r in registrations if rules.get(r.session_id)}
    facts = load_facts(needed) if needed else {}
    names_cache = {}
    changed = []
    newly_by_session = {}
    for registration in registrations:
        rule = rules.get(registration.session_id)
        reasons = []
        if rule:
            person = facts.get(registration.member_id)
            if person is not None:
                key = json.dumps(rule, sort_keys=True)
                if key not in names_cache:
                    names_cache[key] = Names.for_rule(rule)
                outcome = evaluate(rule, person, registration.session.date, names_cache[key])
                if not outcome.ok:
                    reasons = list(outcome.reasons)
        conflict = bool(reasons)
        if conflict == registration.conflict and reasons == (registration.conflict_reasons or []):
            continue
        if conflict and not registration.conflict:
            result.conflicted.append(registration.pk)
            newly_by_session.setdefault(registration.session, []).append(registration.pk)
        elif not conflict:
            result.resolved.append(registration.pk)
        registration.conflict, registration.conflict_reasons = conflict, reasons
        changed.append(registration)
    if changed:
        Registration.objects.bulk_update(changed, ["conflict", "conflict_reasons"])
    for session, ids in newly_by_session.items():
        transaction.on_commit(
            lambda session=session, ids=ids: eligibility_conflict.send(
                sender=Registration, session=session, registration_ids=ids
            )
        )
    return result
