from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, HTML
from crispy_forms.bootstrap import FormActions
from .models import NotificationPreference


class NotificationPreferenceForm(forms.ModelForm):
    """Form for users to manage their notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_new_orders',
            'email_status_updates', 
            'email_bulk_updates',
            'email_pending_reminders',
            'email_daily_summary',
            'email_weekly_report',
            'reminder_frequency_days'
        ]
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        
        # Restrict admin-only fields for non-staff users
        if self.user and not self.user.is_staff:
            self.fields['email_daily_summary'].widget = forms.HiddenInput()
            self.fields['email_weekly_report'].widget = forms.HiddenInput()
        
        self.helper.layout = Layout(
            HTML('<div class="alert alert-info">'
                 '<i class="fas fa-info-circle"></i> '
                 'Verwalten Sie hier Ihre Benachrichtigungseinstellungen für das Bestellsystem.'
                 '</div>'),
            
            Fieldset(
                'E-Mail Benachrichtigungen',
                'email_new_orders',
                'email_status_updates', 
                'email_bulk_updates',
                'email_pending_reminders',
                css_class="mb-4"
            ),
            
            Fieldset(
                'Administrator Benachrichtigungen',
                'email_daily_summary',
                'email_weekly_report',
                css_class="mb-4" if self.user and self.user.is_staff else "d-none"
            ),
            
            Fieldset(
                'Einstellungen',
                'reminder_frequency_days',
                css_class="mb-4"
            ),
            
            FormActions(
                Submit('save', 'Einstellungen speichern', css_class='btn-primary'),
                css_class="text-end"
            )
        )


class AdminNotificationDashboardFilterForm(forms.Form):
    """Filter form for admin notification dashboard"""
    
    NOTIFICATION_TYPE_CHOICES = [
        ('', 'Alle Typen'),
        ('order_created', 'Bestellung erstellt'),
        ('status_update', 'Status geändert'),
        ('bulk_update', 'Massenänderung'),
        ('pending_reminder', 'Erinnerung'),
        ('daily_summary', 'Tägliche Zusammenfassung'),
        ('weekly_report', 'Wöchentlicher Bericht'),
    ]
    
    STATUS_CHOICES = [
        ('', 'Alle Status'),
        ('sent', 'Gesendet'),
        ('failed', 'Fehlgeschlagen'),
        ('pending', 'Ausstehend'),
    ]
    
    notification_type = forms.ChoiceField(
        choices=NOTIFICATION_TYPE_CHOICES,
        required=False,
        label="Benachrichtigungstyp"
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label="Status"
    )
    
    date_from = forms.DateField(
        required=False,
        label="Von Datum",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        label="Bis Datum", 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    recipient_email = forms.EmailField(
        required=False,
        label="Empfänger E-Mail"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Div(
                Div('notification_type', css_class='col-md-3'),
                Div('status', css_class='col-md-3'),
                Div('date_from', css_class='col-md-3'),
                Div('date_to', css_class='col-md-3'),
                css_class='row'
            ),
            Div(
                Div('recipient_email', css_class='col-md-6'),
                Div(
                    Submit('filter', 'Filtern', css_class='btn-primary'),
                    HTML('<a href="?" class="btn btn-secondary ms-2">Zurücksetzen</a>'),
                    css_class='col-md-6 d-flex align-items-end'
                ),
                css_class='row mt-3'
            )
        )
