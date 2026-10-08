"""Render notification e-mails (NOTIF-01.3).

An active database template of the same type (settings → e-mail templates)
overrides the default file; deleting it restores the default. Contexts may
only hold flat values: strings, numbers, booleans, None and lists/dicts of
those. Every value is auto-escaped by Django templates, and the resulting
HTML passes the rich-text sanitizer (SEC-04).
"""

import re

from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from jf_manager_backend.html_safety import sanitize_rich_html

from .email_catalog import CATALOG, template_path

FLAT_TYPES = (str, int, float, bool, type(None))


class NotFlatContext(TypeError):
    pass


def ensure_flat(value, path="context"):
    """Reject model instances, querysets and callables anywhere in the context."""
    if isinstance(value, FLAT_TYPES):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise NotFlatContext(f"{path}: Schlüssel müssen Zeichenketten sein")
            ensure_flat(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            ensure_flat(item, f"{path}[{index}]")
        return
    raise NotFlatContext(f"{path}: {type(value).__name__} ist kein flacher Wert")


def _subject(text):
    # Subjects are single header lines.
    return re.sub(r"\s+", " ", text).strip()


def render(kind, context):
    """(subject, html, text) for a catalogued notification type."""
    if kind not in CATALOG:
        raise KeyError(kind)
    ensure_flat(context)
    from orders.notifications.template_service import TemplateRenderer

    custom = TemplateRenderer.get_email_template(kind)
    if custom is not None:
        subject, html, text = TemplateRenderer._render_custom_template(custom, context)
        return _subject(subject), html, text
    entry = CATALOG[kind]
    subject = _subject(Template(entry["subject"]).render(Context(context, autoescape=False)))
    content = render_to_string(template_path(kind), context)
    html = TemplateRenderer._apply_layout(entry["layout"], content, context, subject)
    html = sanitize_rich_html(html)
    return subject, html, strip_tags(html)


def default_source(kind):
    """Default template source for the editor's "reset to default" (settings)."""
    from django.template.loader import get_template

    return get_template(template_path(kind)).template.source


LINK_PATTERN = r"\{\{\s*%s\s*\}\}"


def missing_links(kind, html_template):
    """Required links (4.9.3 item 5, E17) a customised template must keep."""
    entry = CATALOG.get(kind)
    if not entry:
        return []
    if re.search(r"\{%\s*include\s+[\"']notifications/emails/_footer\.html[\"']", html_template):
        return []  # the shared footer carries open, preferences and the status-dependent withdraw link
    return [link for link in entry["required_links"] if not re.search(LINK_PATTERN % re.escape(link), html_template)]
