from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from .utils import get_attachment_file_path


class Attachment(models.Model):
    """
    Generic attachment model that can be attached to any model instance.
    """
    class Meta:
        verbose_name = "Anhang"
        verbose_name_plural = "Anhänge"
        ordering = ['-uploaded_at']

    # Generic foreign key to attach to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # File and metadata
    file = models.FileField(
        upload_to=get_attachment_file_path,
        verbose_name="Datei",
        help_text="Zulässige Dateiformate: PDF, DOC, DOCX, JPG, PNG, GIF"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Name",
        help_text="Beschreibender Name für den Anhang"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Beschreibung",
        help_text="Optionale Beschreibung des Anhangs"
    )
    
    # Metadata
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Hochgeladen am"
    )
    uploaded_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Hochgeladen von"
    )
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Dateigröße (Bytes)"
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="MIME-Typ"
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Set file metadata
        if self.file:
            self.file_size = self.file.size
            # Try to determine MIME type from file extension
            file_extension = self.file.name.split('.')[-1].lower()
            mime_types = {
                'pdf': 'application/pdf',
                'doc': 'application/msword',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'txt': 'text/plain',
            }
            self.mime_type = mime_types.get(file_extension, 'application/octet-stream')
        
        super().save(*args, **kwargs)

    def get_file_extension(self):
        """Get the file extension."""
        if self.file:
            return self.file.name.split('.')[-1].lower()
        return ''

    def is_image(self):
        """Check if the attachment is an image."""
        return self.mime_type.startswith('image/')

    def is_pdf(self):
        """Check if the attachment is a PDF."""
        return self.mime_type == 'application/pdf'

    def get_download_url(self):
        """Get the download URL for the file."""
        if self.file:
            return self.file.url
        return None

    def get_file_size_human(self):
        """Get human-readable file size."""
        if not self.file_size:
            return "Unbekannt"
        
        # Convert bytes to human readable format
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
