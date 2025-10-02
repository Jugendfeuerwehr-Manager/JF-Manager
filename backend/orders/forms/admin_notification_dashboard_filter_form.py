from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML


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
