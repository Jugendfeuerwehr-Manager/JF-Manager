"""One allowlist for user-authored HTML stored or returned by the API."""

import re
from html import escape

import nh3
from rest_framework import serializers


def _safe_attribute(tag: str, attribute: str, value: str) -> str | None:
    # Deliberately small CSS grammar: no functions, escapes, comments or at-rules.
    # nh3 then parses declarations and restricts properties. This preserves common
    # mail typography/spacing while excluding URL loads and legacy expressions.
    if attribute == "style" and not re.fullmatch(r"[a-zA-Z0-9#;:,.%!'\"\s-]*", value):
        return None
    if tag == "img" and attribute == "src" and not value.lower().startswith(("https://", "http://")):
        return None
    return value


_CLEANER = nh3.Cleaner(
    tags={
        "img",
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
        "h1",
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
    attributes={
        "*": {"style"},
        "a": {"href"},
        "img": {"src", "alt", "width", "height"},
        "table": {"width", "cellpadding", "cellspacing", "border"},
        "th": {"colspan", "rowspan", "align", "valign"},
        "td": {"colspan", "rowspan", "align", "valign"},
    },
    attribute_filter=_safe_attribute,
    filter_style_properties={
        "color",
        "background-color",
        "font-family",
        "font-size",
        "font-weight",
        "font-style",
        "text-align",
        "text-decoration",
        "line-height",
        "letter-spacing",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "border",
        "border-radius",
        "border-color",
        "border-width",
        "border-style",
        "border-collapse",
        "width",
        "max-width",
        "height",
        "vertical-align",
    },
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
