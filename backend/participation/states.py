"""Registration state machine (PART-01.1, concept 4.5) as a pure, table-driven function.

``current`` is ``None`` for a person without a row ("expected" in opt-out, "no response" otherwise).
``target`` is what the caller asks for: ``registered``, ``cancelled``, ``applied`` or ``withdrawn``.

Semantics worth knowing:

* opt_out: ``cancelled`` records the absence, ``registered`` takes it back (the row stays, state
  ``registered`` means "confirmed/expected"; nothing is ever deleted).
* opt_in: ``registered`` becomes ``waitlisted`` when the session is full; ``cancelled`` also gives
  back a waitlist place.
* assignment: ``applied`` applies, ``withdrawn`` takes an application back (state ``cancelled``),
  ``cancelled`` leaves an assigned place. ``assigned``/``not_selected`` are set by staff (PART-04).
"""

from dataclasses import dataclass

REGISTERED, WAITLISTED, APPLIED = "registered", "waitlisted", "applied"
ASSIGNED, NOT_SELECTED, CANCELLED = "assigned", "not_selected", "cancelled"
WITHDRAWN = "withdrawn"

OPT_OUT, OPT_IN, ASSIGNMENT = "opt_out", "opt_in", "assignment"

MODES = (OPT_OUT, OPT_IN, ASSIGNMENT)
STATES = (REGISTERED, WAITLISTED, APPLIED, ASSIGNED, NOT_SELECTED, CANCELLED)
TARGETS = (REGISTERED, CANCELLED, APPLIED, WITHDRAWN)

MODE_FORBIDDEN = "mode_forbidden"
INVALID_TRANSITION = "invalid_transition"

# Targets a mode knows at all.
MODE_TARGETS = {
    OPT_OUT: (REGISTERED, CANCELLED),
    OPT_IN: (REGISTERED, CANCELLED),
    ASSIGNMENT: (APPLIED, WITHDRAWN, CANCELLED),
}

# Marker: the new state is "registered", or "waitlisted" when no place is free.
_SEAT = "seat"

_ANY = (None, *STATES)
_LEFTOVERS = (WAITLISTED, APPLIED, ASSIGNED, NOT_SELECTED)  # states of another mode after a mode switch


def _build():
    table = {}

    def put(mode, currents, target, result):
        for current in currents:
            table[(mode, current, target)] = result

    # opt_out
    put(OPT_OUT, (None, REGISTERED, *_LEFTOVERS), CANCELLED, CANCELLED)
    put(OPT_OUT, (CANCELLED,), CANCELLED, CANCELLED)
    put(OPT_OUT, (None, CANCELLED, REGISTERED), REGISTERED, REGISTERED)
    # opt_in
    put(OPT_IN, (None, CANCELLED, REGISTERED, WAITLISTED), REGISTERED, _SEAT)
    put(OPT_IN, (None, REGISTERED, WAITLISTED, CANCELLED, *_LEFTOVERS[1:]), CANCELLED, CANCELLED)
    # assignment
    put(ASSIGNMENT, (None, CANCELLED, APPLIED), APPLIED, APPLIED)
    put(ASSIGNMENT, (APPLIED,), WITHDRAWN, CANCELLED)
    put(ASSIGNMENT, (None, APPLIED, ASSIGNED, REGISTERED, CANCELLED), CANCELLED, CANCELLED)
    return table


TRANSITIONS = _build()


@dataclass(frozen=True)
class Outcome:
    state: str | None = None  # new state; None with ``code`` set means refused
    code: str | None = None  # MODE_FORBIDDEN | INVALID_TRANSITION
    noop: bool = False  # target equals the current state

    @property
    def ok(self):
        return self.code is None


def next_state(mode, current, target, *, full=False):
    """Return the ``Outcome`` of asking for ``target`` from ``current`` in ``mode``."""
    if mode not in MODES or target not in TARGETS or (current is not None and current not in STATES):
        return Outcome(code=INVALID_TRANSITION)
    if target not in MODE_TARGETS[mode]:
        return Outcome(code=MODE_FORBIDDEN)
    result = TRANSITIONS.get((mode, current, target))
    if result is None:
        return Outcome(code=INVALID_TRANSITION)
    if result == _SEAT:
        if current in (REGISTERED, WAITLISTED):
            result = current  # already holds a seat or a waitlist place: nothing changes
        else:
            result = WAITLISTED if full else REGISTERED
    return Outcome(state=result, noop=result == current)
