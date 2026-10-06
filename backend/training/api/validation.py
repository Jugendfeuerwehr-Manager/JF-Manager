"""Time invariants shared by individual writes and complete plan drafts."""

from rest_framework.exceptions import ValidationError


def validate_session_times(start, end):
    if end <= start:
        raise ValidationError({"end_time": "Ende muss am selben Tag nach Beginn liegen."})
    return (
        (end.hour * 3600 + end.minute * 60 + end.second) - (start.hour * 3600 + start.minute * 60 + start.second)
    ) / 60


def validate_block_times(offset, duration, session_duration):
    errors = {}
    if offset < 0:
        errors["start_offset_minutes"] = "Beginn darf nicht vor dem Termin liegen."
    if duration <= 0:
        errors["duration_minutes"] = "Dauer muss positiv sein."
    if offset + duration > session_duration:
        errors["duration_minutes"] = "Der Baustein endet außerhalb des Terminrahmens."
    if errors:
        raise ValidationError(errors)
