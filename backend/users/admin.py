from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from rest_framework.authtoken.admin import TokenAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    fieldsets = UserAdmin.fieldsets + (
        ('DSGVO', {
            'classes': ('wide',),
            'fields': ('dsgvo_internal', 'dsgvo_external'),
        }),
        ('Kontakt', {'fields': ('phone', 'mobile_phone', 'street', 'zip_code', 'city')}),
        ('Weiteres', {'fields': ('avatar',)}),
    )
    list_filter = UserAdmin.list_filter + ('dsgvo_internal', 'dsgvo_external')
    list_display = ['username', 'email', 'is_staff', 'dsgvo_internal', 'dsgvo_external']

admin.site.register(CustomUser, CustomUserAdmin)


TokenAdmin.raw_id_fields = ['user']