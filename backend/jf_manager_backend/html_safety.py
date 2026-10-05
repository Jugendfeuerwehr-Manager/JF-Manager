"""One allowlist for user-authored HTML stored or returned by the API."""

from html import escape

import nh3
from rest_framework import serializers

_CLEANER = nh3.Cleaner(
    tags={
        "p",
        "br",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "s",
        "a",
        "ul",
        "ol",
        "li",
        "blockquote",
        "h2",
        "h3",
        "div",
        "span",
        "hr",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    },
    clean_content_tags={"script", "style", "iframe", "svg", "math", "object", "embed", "template"},
    attributes={"a": {"href"}, "th": {"colspan", "rowspan"}, "td": {"colspan", "rowspan"}},
    url_schemes={"http", "https", "mailto"},
    url_relative="deny",
    link_rel="noopener noreferrer nofollow",
)


def sanitize_rich_html(value: str | None) -> str:
    """Keep limited formatting and discard active markup, attributes and URLs."""
    return _CLEANER.clean(value or "")


def escape_html_text(value: str | None) -> str:
    """Insert a plain text value into an HTML text position."""
    return escape(value or "", quote=True)


class SanitizedHTMLField(serializers.CharField):
    """Sanitize new rich text and legacy database values at the API boundary."""

    def to_internal_value(self, data):
        return sanitize_rich_html(super().to_internal_value(data))

    def to_representation(self, value):
        return sanitize_rich_html(super().to_representation(value))
