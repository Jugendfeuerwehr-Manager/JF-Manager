from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from dynamic_preferences.admin import GlobalPreferenceAdmin
from dynamic_preferences.models import GlobalPreferenceModel


class EmailTestForm(forms.Form):
    recipient = forms.EmailField(
        label='Empfänger E-Mail',
        help_text='E-Mail-Adresse an die eine Test-E-Mail gesendet werden soll'
    )
    subject = forms.CharField(
        label='Betreff',
        initial='Test E-Mail vom JF-Manager'
    )
    message = forms.CharField(
        label='Nachricht',
        widget=forms.Textarea,
        initial='Dies ist eine Test-E-Mail vom JF-Manager System.'
    )


class CustomGlobalPreferenceAdmin(GlobalPreferenceAdmin):
    """
    Custom admin for global preferences with test email functionality
    """
    change_list_template = 'admin/preferences_change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('test-email/', self.admin_site.admin_view(self.test_email_view), name='test_email'),
        ]
        return custom_urls + urls

    def test_email_view(self, request):
        """Admin view to test email settings"""
        if request.method == 'POST':
            form = EmailTestForm(request.POST)
            if form.is_valid():
                recipient = form.cleaned_data['recipient']
                subject = form.cleaned_data['subject']
                message = form.cleaned_data['message']
                
                try:
                    # Get current email settings from Django settings
                    from_email = settings.DEFAULT_FROM_EMAIL
                    
                    # Send test email
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=from_email,
                        recipient_list=[recipient],
                        fail_silently=False,
                    )
                    
                    # Show success message
                    messages.success(
                        request, 
                        f'Test-E-Mail erfolgreich gesendet an {recipient} von {from_email}. '
                        f'Aktuelle SMTP-Einstellungen: Host={settings.EMAIL_HOST}, '
                        f'Port={settings.EMAIL_PORT}, TLS={settings.EMAIL_USE_TLS}, '
                        f'SSL={settings.EMAIL_USE_SSL}'
                    )
                    
                    # Redirect back to admin
                    return HttpResponseRedirect(reverse('admin:dynamic_preferences_globalpreferencemodel_changelist'))
                
                except Exception as e:
                    # Show error message
                    messages.error(
                        request, 
                        f'Fehler beim Senden der Test-E-Mail: {str(e)}. '
                        f'Bitte überprüfen Sie die SMTP-Einstellungen.'
                    )
        else:
            form = EmailTestForm()
        
        # Display email settings
        context = {
            'form': form,
            'title': 'E-Mail Einstellungen testen',
            'email_settings': {
                'EMAIL_HOST': settings.EMAIL_HOST,
                'EMAIL_PORT': settings.EMAIL_PORT,
                'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
                'EMAIL_HOST_PASSWORD': '*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else '',
                'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
                'EMAIL_USE_SSL': settings.EMAIL_USE_SSL,
                'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
            }
        }
        
        return render(request, 'admin/test_email.html', context)


# Unregister the default admin and register our custom admin
admin.site.unregister(GlobalPreferenceModel)
admin.site.register(GlobalPreferenceModel, CustomGlobalPreferenceAdmin)
