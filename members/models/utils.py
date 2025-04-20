import uuid
import os
from django.conf import settings


def get_file_path(instance, filename):
    """
    filename = "%s_%s.%s" % (instance.id, uuid.uuid4(), file_extension)

    Args:
        instance: The instance this file is associated with.
        filename: The original name of the file.

    Returns:
        str: The generated file path.
    """
    file_extension = filename.split('.')[-1]
    filename = "%s.%s" % (uuid.uuid4(), file_extension)
    return os.path.join(settings.MEDIA_ROOT, filename)
