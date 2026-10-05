"""Shared responses for files after the caller has authorized their owner."""

from pathlib import Path

from django.http import FileResponse, Http404


def private_file_response(field, *, filename=None, download=False):
    if not field:
        raise Http404
    try:
        stream = field.open("rb")
        signature = stream.read(16)
        stream.seek(0)
    except (FileNotFoundError, OSError) as exc:
        raise Http404 from exc
    # Never trust the client-supplied MIME type or extension for an inline response.
    content_type = "application/octet-stream"
    if signature.startswith(b"\x89PNG\r\n\x1a\n"):
        content_type = "image/png"
    elif signature.startswith(b"\xff\xd8\xff"):
        content_type = "image/jpeg"
    elif signature.startswith((b"GIF87a", b"GIF89a")):
        content_type = "image/gif"
    elif signature.startswith(b"RIFF") and signature[8:12] == b"WEBP":
        content_type = "image/webp"
    elif signature.startswith(b"%PDF-"):
        content_type = "application/pdf"
    response = FileResponse(
        stream,
        as_attachment=download or content_type == "application/octet-stream",
        filename=filename or Path(field.name).name,
        content_type=content_type,
    )
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Cookie, Authorization"
    response["Referrer-Policy"] = "no-referrer"
    response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    response["X-Content-Type-Options"] = "nosniff"
    return response
