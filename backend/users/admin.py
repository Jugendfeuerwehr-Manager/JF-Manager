from django.contrib import admin

# Register your models here.
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = "__all__"


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = "__all__"


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    fieldsets = (
        *UserAdmin.fieldsets,
        ("DSGVO", {"classes": ("wide",), "fields": ("dsgvo_internal", "dsgvo_external")}),
        ("Kontakt", {"fields": ("phone", "mobile_phone", "street", "zip_code", "city")}),
        ("Weiteres", {"fields": ("avatar",)}),
    )
    list_filter = (*UserAdmin.list_filter, "dsgvo_internal", "dsgvo_external")
    list_display = ["username", "email", "is_staff", "dsgvo_internal", "dsgvo_external"]


admin.site.register(CustomUser, CustomUserAdmin)
