import os
import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction


def training_media_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"training/images/{uuid.uuid4()}{ext}"


class TrainingMedia(models.Model):
    """
    Image/file uploaded directly into a block's rich-text editor.
    Linked to either a LibraryBlock or TrainingBlock via GenericFK.
    Allows cleanup when the parent block is deleted.
    """

    class Meta:
        verbose_name = "Trainings-Mediendatei"
        verbose_name_plural = "Trainings-Mediendateien"
        ordering = ["-created_at"]

    # Generic FK — can point to LibraryBlock or TrainingBlock
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    file = models.ImageField(
        upload_to=training_media_upload_path,
        verbose_name="Bild",
    )
    original_filename = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Originaldateiname",
    )
    uploaded_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Hochgeladen von",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.file and not self.file._committed:
            from jf_manager_backend.upload_safety import validate_owner_capacity, validate_upload

            validate_upload(self.file, image_only=True)
            validate_owner_capacity(self.content_object, self.file, exclude_media=self.pk)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.original_filename or str(self.file)

    @property
    def url(self):
        if self.file:
            from jf_manager_backend.private_media import private_media_url

            return private_media_url("training", self.pk)
        return ""
