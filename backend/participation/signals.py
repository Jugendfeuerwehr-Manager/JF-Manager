"""Signals other apps can connect to (NOTIF-01); nothing is delivered from here."""

from django.dispatch import Signal

# Sent with ``session`` once a planned service became published (and so registrable), after commit.
session_published = Signal()

# Sent with ``session`` and ``registration_ids`` (newly flagged ``Registration.conflict``, PART-03.5), after commit.
eligibility_conflict = Signal()

# Sent after commit when a published, not yet started and portal-visible service was moved, changed
# (place) or cancelled. Arguments: ``session``, ``kind`` ("moved" | "cancelled" | "changed"), ``old`` and
# ``new`` (dicts with ``date``, ``start_time``, ``end_time``, ``place``) and ``member_ids`` (sorted list:
# registered, waitlisted, applied or assigned people and, in opt-out services, the target group minus the
# cancelled ones). Eligibility is not applied; receivers decide whom to notify.
session_changed = Signal()
