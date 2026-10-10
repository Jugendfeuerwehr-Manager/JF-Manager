"""Upload limits and format checks shared by every private upload path."""

import io
import warnings
import zipfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.exceptions import ValidationError

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_OWNER_BYTES = 50 * 1024 * 1024
MAX_OWNER_FILES = 20


def validate_upload(upload, *, image_only=False):
    if upload.size > MAX_FILE_BYTES or upload.size == 0:
        raise ValidationError({"file": "Datei ist leer oder zu groß (max. 10 MB)."})
    extension = Path(upload.name).suffix.lower()
    try:
        upload.seek(0)
        head = upload.read(16)
        upload.seek(0)
        if extension in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(upload) as image:
                    expected = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".gif": "GIF", ".webp": "WEBP"}[
                        extension
                    ]
                    if image.format != expected or image.width * image.height > 25_000_000:
                        raise ValueError("Bildformat oder Bildabmessungen ungültig")
                    image.verify()
            return "image/jpeg" if extension in {".jpg", ".jpeg"} else f"image/{extension[1:]}"
        if image_only:
            raise ValueError("Nur JPEG, PNG, GIF oder WebP erlaubt")
        if extension == ".pdf" and head.startswith(b"%PDF-"):
            return "application/pdf"
        if extension in {".doc", ".xls"} and head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            return "application/msword" if extension == ".doc" else "application/vnd.ms-excel"
        if extension in {".docx", ".xlsx"}:
            with zipfile.ZipFile(upload) as archive:
                entries = archive.infolist()
                if len(entries) > 2000 or sum(entry.file_size for entry in entries) > MAX_OWNER_BYTES:
                    raise ValueError("Office-Datei entpackt zu groß")
                required = "word/document.xml" if extension == ".docx" else "xl/workbook.xml"
                names = {entry.filename for entry in entries}
                if (
                    required not in names
                    or "[Content_Types].xml" not in names
                    or any("vbaproject" in name.lower() for name in names)
                ):
                    raise ValueError("Office-Format ungültig oder Makros enthalten")
            return "application/vnd.openxmlformats-officedocument." + (
                "wordprocessingml.document" if extension == ".docx" else "spreadsheetml.sheet"
            )
        if extension in {".txt", ".csv"}:
            text = upload.read().decode("utf-8-sig")
            if "\x00" in text:
                raise ValueError("Binärinhalt in Textdatei")
            return "text/plain" if extension == ".txt" else "text/csv"
        raise ValueError("Dateiformat nicht erlaubt oder Inhalt passt nicht zur Endung")
    except (
        ValueError,
        OSError,
        SyntaxError,
        zipfile.BadZipFile,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise ValidationError(
            {
                "file": "Dateiformat nicht erlaubt oder Dateiinhalt ungültig. Erlaubt: Bilder, PDF, Word, Excel, UTF-8-Text/CSV."
            }
        ) from exc
    finally:
        upload.seek(0)


def clean_avatar(upload):
    validate_upload(upload, image_only=True)
    with Image.open(upload) as image:
        image = image.convert("RGB")
        image.thumbnail((1200, 1200))
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=85)
    return SimpleUploadedFile("avatar.jpg", output.getvalue(), content_type="image/jpeg")


def validate_batch(files):
    if len(files) > MAX_OWNER_FILES or sum(file.size for file in files) > MAX_OWNER_BYTES:
        raise ValidationError({"file": "Maximal 20 Dateien mit zusammen 50 MB erlaubt."})
    return [validate_upload(file) for file in files]


def validate_owner_capacity(owner, incoming, *, exclude_attachment=None, exclude_media=None):
    """Called within atomic save; lock the shared owner before counting both collections."""
    from django.contrib.contenttypes.models import ContentType

    from members.models import Attachment
    from training.models import TrainingMedia

    type(owner).objects.select_for_update().get(pk=owner.pk)
    content_type = ContentType.objects.get_for_model(owner)
    attachments = Attachment.objects.filter(content_type=content_type, object_id=owner.pk).exclude(
        pk=exclude_attachment
    )
    media = TrainingMedia.objects.filter(content_type=content_type, object_id=owner.pk).exclude(pk=exclude_media)
    files = [row.file for row in attachments if row.file] + [row.file for row in media if row.file]
    if len(files) + 1 > MAX_OWNER_FILES or sum(file.size for file in files) + incoming.size > MAX_OWNER_BYTES:
        raise ValidationError({"file": "Maximal 20 Dateien mit zusammen 50 MB je Objekt erlaubt."})
