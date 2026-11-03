"""Editing and publishing application forms."""

import copy
import hashlib
import json

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from admissions.form_template import jf_template
from admissions.models import AdmissionForm, AdmissionFormVersion, AdmissionTextBlock
from admissions.schema import check_schema, check_structure, iter_elements
from jf_manager_backend.html_safety import sanitize_rich_html
from privacy.models import ConsentKind, LegalPage
from privacy.services import legal


def canonical_hash(payload):
    """SHA-256 of the canonical JSON form (sorted keys, UTF-8, no whitespace)."""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def available_references():
    """Legal texts and consent kinds a form may point at."""
    return {
        "legal_kinds": [{"value": value, "label": label} for value, label in LegalPage.Kind.choices],
        "consent_kinds": list(
            ConsentKind.objects.filter(active=True).order_by("position", "label").values("slug", "label", "description")
        ),
    }


def _reference_slugs():
    return {
        "legal_kinds": set(LegalPage.Kind.values),
        "consent_kinds": set(ConsentKind.objects.filter(active=True).values_list("slug", flat=True)),
    }


def check(schema, *, for_publish=False):
    return check_schema(schema, for_publish=for_publish, **_reference_slugs())


def sanitize_draft(schema):
    """Clean rich text right away: the builder preview renders drafts as HTML."""
    clean = copy.deepcopy(schema)
    for _, element in iter_elements(clean):
        if isinstance(element, dict) and element.get("type") == "richtext":
            element["html"] = sanitize_rich_html(element.get("html") or "")
    return clean


def create_form(*, department, title, from_template=True, by=None):
    return AdmissionForm.objects.create(
        department=department,
        title=title,
        draft_schema=jf_template() if from_template else {"pages": []},
        updated_by=by,
    )


def save_draft(form, schema, *, by=None):
    """Store the draft. Unfinished elements are allowed; broken structure is not."""
    structural = check_structure(schema)
    if structural:
        raise ValidationError({"draft_schema": structural})
    errors = check(schema)
    form.draft_schema = schema
    form.updated_by = by
    form.save(update_fields=["draft_schema", "updated_by", "updated_at"])
    return errors


def snapshot(schema, department_id):
    """Copy text blocks, legal texts and consent wording into the schema so the version stands alone."""
    frozen = copy.deepcopy(schema)
    missing = []
    blocks = {block.pk: block for block in AdmissionTextBlock.objects.filter(department_id__in=[department_id, None])}
    kinds = {kind.slug: kind for kind in ConsentKind.objects.filter(active=True)}
    for path, element in iter_elements(frozen):
        if element["type"] == "richtext":
            block = blocks.get(element.get("text_block"))
            if element.get("text_block") and block is None:
                missing.append({"path": path, "message": "Der Textbaustein ist nicht verfügbar."})
                continue
            element["html"] = sanitize_rich_html(block.body if block else element.get("html", ""))
        elif element["type"] == "legal_ack":
            page = legal.published(element["legal_kind"])
            if page is None:
                missing.append({"path": path, "message": "Der Rechtstext ist noch nicht veröffentlicht."})
                continue
            element["legal"] = {
                "title": page.title,
                "body": page.body,
                "version": legal.version_label(element["legal_kind"]),
            }
        elif element["type"] == "consent":
            kind = kinds[element["consent_kind"]]
            element["consent"] = {"label": kind.label, "text": kind.description, "version": kind.text_version}
    return frozen, missing


def publish(form, *, by=None, change_note=""):
    """Freeze the draft as the next version."""
    errors = check(form.draft_schema, for_publish=True)
    if errors:
        raise ValidationError({"draft_schema": errors})
    schema, missing = snapshot(form.draft_schema, form.department_id)
    if missing:
        raise ValidationError({"draft_schema": missing})

    with transaction.atomic():
        AdmissionForm.objects.select_for_update().get(pk=form.pk)
        last = form.versions.aggregate(last=Max("version"))["last"] or 0
        content = {"title": form.title, "intro": form.intro, "signature_mode": form.signature_mode, "schema": schema}
        return AdmissionFormVersion.objects.create(
            form=form,
            version=last + 1,
            title=form.title,
            intro=form.intro,
            signature_mode=form.signature_mode,
            schema=schema,
            schema_hash=canonical_hash(content),
            change_note=change_note,
            published_by=by,
        )
