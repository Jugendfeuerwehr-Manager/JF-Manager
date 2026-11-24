"""Re-checking seals against the records they cover."""

from admissions.models import AdmissionDecision, Application, Seal
from admissions.services import seal as seal_service
from admissions.services.decisions import decision_content
from admissions.services.submission import SUBJECT, submission_content


def _content_for(stored):
    """Current content of the sealed record, or None if it cannot be rebuilt (deleted, export)."""
    if stored.subject_type != SUBJECT:
        return None
    application = Application.objects.filter(pk=stored.subject_id).select_related("form_version").first()
    if application is None:
        return None
    if stored.kind == Seal.Kind.SUBMISSION:
        return submission_content(application)
    if stored.kind == Seal.Kind.DECISION:
        decisions = AdmissionDecision.objects.filter(application=application).select_related("meeting")
        # The decision recorded right before the seal; decisions are never edited or removed.
        decision = decisions.filter(recorded_at__lte=stored.created_at).order_by("-recorded_at").first()
        return decision_content(decision) if decision else None
    return None


def verify_application(application):
    """All seals of an application with their findings, oldest first."""
    results = []
    for stored in seal_service.chain(SUBJECT, application.pk):
        content = _content_for(stored)
        result = seal_service.verify(stored, content)
        result["content_checked"] = content is not None or stored.kind == Seal.Kind.EXPORT
        results.append(result)
    return {"valid": all(result["valid"] for result in results) and bool(results), "seals": results}


def verify_public(public_id):
    """Findings for the public check page; no personal data."""
    stored = Seal.objects.filter(public_id=public_id).first()
    if stored is None:
        return None
    content = _content_for(stored)
    result = seal_service.verify(stored, content)
    return {
        "valid": result["valid"],
        "kind": stored.get_kind_display(),
        "sealed_at": stored.created_at,
        "content_checked": content is not None,
        "signature": result["signature"],
        "chain": result["chain"],
    }
