import io
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from phonenumber_field.modelfields import PhoneNumberField
from PIL import Image as Img

# Create your models here.
class CustomUser(AbstractUser):
    # add additional fields in here

    dsgvo_internal = models.BooleanField(default=False)
    dsgvo_external = models.BooleanField(default=False)

    phone = PhoneNumberField(blank=True)
    mobile_phone = PhoneNumberField(blank=True)
    street = models.CharField(max_length=200, blank=True, default='')
    zip_code = models.CharField(max_length=200, blank=True, default='')
    city = models.CharField(max_length=200, blank=True, default='')


    # TODO: Add pre_delete hook to make sure to remove the file, not just the DB Recoard.
    avatar = models.ImageField(blank=True)

    def __str__(self):
        if self.last_name and self.first_name:
            return self.get_full_name()
        else:
            return self.username

    def get_absolute_url(self):
        return reverse('users:profile', kwargs={'pk': self.pk})

    """
    As we do not want users to save their 10MB DSLR Picutres on our Disk, we compress them on save.
    """
    def save(self, *args, **kwargs):
        if self.avatar:
            img = Img.open(io.StringIO.StringIO(self.avatar.read()))
            if img.mode != 'RGB':
                img = img.convert('RGB')

            new_width = 500
            img.thumbnail((new_width, new_width * self.image.height / self.image.width), Img.ANTIALIAS)

            output = io.StringIO.StringIO()
            img.save(output, format='JPEG', quality=70)
            output.seek(0)
            self.image = InMemoryUploadedFile(output, 'ImageField', "%s.jpg" % self.image.name.split('.')[0],
                                              'image/jpeg', output.len, None)
        super(CustomUser, self).save(*args, **kwargs)
