from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from django.core.files.images import get_image_dimensions
from .models import CustomUser



class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('avatar', 'phone', 'mobile_phone', 'street', 'zip_code', 'city', 'dsgvo_internal',
                  'dsgvo_external', 'email')

    def clean_avatar(self):
        avatar = self.cleaned_data['avatar']

        try:
            #validate content type
            main, sub = avatar.content_type.split('/')
            if not (main == 'image' and sub in ['jpeg', 'pjpeg', 'gif', 'png']):
                raise forms.ValidationError(u'Please use a JPEG, '
                    'GIF or PNG image.')

        except AttributeError:
            """
            Handles case when we are updating the user profile
            and do not supply a new avatar
            """
            pass

        return avatar


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = CustomUser
        fields = ('username', 'email')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email')