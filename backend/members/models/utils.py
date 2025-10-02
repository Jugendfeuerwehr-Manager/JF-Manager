import uuid
import os
from django.conf import settings


def get_file_path(instance, filename):
    """
    Generate a unique file path for uploads.

    Args:
        instance: The instance this file is associated with.
        filename: The original name of the file.

    Returns:
        str: The generated file path relative to MEDIA_ROOT.
    """
    file_extension = filename.split('.')[-1]
    unique_filename = "%s.%s" % (uuid.uuid4(), file_extension)
    
    # Use configurable folder path
    upload_folder = getattr(settings, 'MEMBER_UPLOAD_FOLDER', 'members/avatars')
    return os.path.join(upload_folder, unique_filename)


def get_attachment_file_path(instance, filename):
    """
    Generate a unique file path for attachment uploads.

    Args:
        instance: The attachment instance.
        filename: The original name of the file.

    Returns:
        str: The generated file path relative to MEDIA_ROOT.
    """
    file_extension = filename.split('.')[-1]
    unique_filename = "%s.%s" % (uuid.uuid4(), file_extension)
    
    # Determine the app based on the content_type if available
    app_name = 'general'
    if hasattr(instance, 'content_type') and instance.content_type:
        app_name = instance.content_type.app_label
    
    # Use configurable folder path
    base_folder = getattr(settings, 'ATTACHMENT_UPLOAD_FOLDER', 'attachments')
    return os.path.join(base_folder, app_name, unique_filename)
