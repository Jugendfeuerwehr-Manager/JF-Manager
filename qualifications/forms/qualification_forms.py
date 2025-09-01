from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Field, Row, Column, HTML
from crispy_forms.bootstrap import PrependedText
from dateutil.relativedelta import relativedelta
from datetime import date

from ..models import QualificationType, Qualification
from ..widgets import UserSelect2Widget, MemberSelect2Widget


class QualificationTypeForm(forms.ModelForm):
    class Meta:
        model = QualificationType
        fields = ['name', 'expires', 'validity_period', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('expires', css_class='form-group col-md-3 mb-0'),
                Column('validity_period', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            'description',
            Div(
                Submit('submit', 'Speichern', css_class='btn btn-primary'),
                HTML('<a href="#" onclick="history.back()" class="btn btn-secondary ms-2"><i class="fas fa-times"></i> Abbrechen</a>'),
                css_class='d-flex gap-2'
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        expires = cleaned_data.get('expires')
        validity_period = cleaned_data.get('validity_period')

        if expires and not validity_period:
            raise ValidationError('Bei ablaufenden Qualifikationen muss eine Gültigkeitsdauer angegeben werden.')
        
        if not expires and validity_period:
            cleaned_data['validity_period'] = None

        return cleaned_data


class QualificationForm(forms.ModelForm):
    class Meta:
        model = Qualification
        fields = ['type', 'user', 'member', 'date_acquired', 'date_expires', 'issued_by', 'note']
        widgets = {
            'user': UserSelect2Widget(),
            'member': MemberSelect2Widget(),
            'date_acquired': forms.DateInput(attrs={'type': 'date'}),
            'date_expires': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # Optional: Vorauswahl von User oder Member
        initial_user = kwargs.pop('initial_user', None)
        initial_member = kwargs.pop('initial_member', None)
        
        super().__init__(*args, **kwargs)
        
        if initial_user:
            self.fields['user'].initial = initial_user
            self.fields['member'].widget = forms.HiddenInput()
        elif initial_member:
            self.fields['member'].initial = initial_member
            self.fields['user'].widget = forms.HiddenInput()

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'type',
            Row(
                Column('user', css_class='form-group col-md-6 mb-0'),
                Column('member', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('date_acquired', css_class='form-group col-md-4 mb-0'),
                Column('date_expires', css_class='form-group col-md-4 mb-0'),
                Column('issued_by', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'note',
            Div(
                Submit('submit', 'Speichern', css_class='btn btn-primary'),
                HTML('<a href="#" onclick="history.back()" class="btn btn-secondary ms-2"><i class="fas fa-times"></i> Abbrechen</a>'),
                css_class='d-flex gap-2'
            ),
        )

        # Auto-berechnung des Ablaufdatums via JavaScript
        self.helper.form_id = 'qualification-form'

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        member = cleaned_data.get('member')
        qualification_type = cleaned_data.get('type')
        date_acquired = cleaned_data.get('date_acquired')

        # Mindestens User oder Member
        if not user and not member:
            raise ValidationError('Entweder Benutzer oder Mitglied muss ausgewählt werden.')
        
        # Nicht beide gleichzeitig
        if user and member:
            raise ValidationError('Nur Benutzer oder Mitglied kann ausgewählt werden, nicht beide.')

        # Automatisches Setzen des Ablaufdatums
        if qualification_type and qualification_type.expires and date_acquired:
            if not cleaned_data.get('date_expires') and qualification_type.validity_period:
                cleaned_data['date_expires'] = date_acquired + relativedelta(months=qualification_type.validity_period)

        return cleaned_data


class QualificationFilterForm(forms.Form):
    """Filter-Form für die Qualifikations-Übersicht"""
    
    STATUS_CHOICES = [
        ('', 'Alle'),
        ('active', 'Gültig'),
        ('expiring', 'Läuft bald ab'),
        ('expired', 'Abgelaufen'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label='Status'
    )
    qualification_type = forms.ModelChoiceField(
        queryset=QualificationType.objects.all(),
        required=False,
        empty_label='Alle Typen',
        label='Qualifikationstyp'
    )
    search = forms.CharField(
        max_length=100,
        required=False,
        label='Suche',
        widget=forms.TextInput(attrs={'placeholder': 'Name, Typ, Aussteller...'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'mb-4'
        self.helper.layout = Layout(
            Row(
                Column('status', css_class='form-group col-md-3 mb-0'),
                Column('qualification_type', css_class='form-group col-md-3 mb-0'),
                Column('search', css_class='form-group col-md-4 mb-0'),
                Column(
                    Submit('filter', 'Filtern', css_class='btn btn-primary'),
                    css_class='form-group col-md-2 mb-0 d-flex align-items-end'
                ),
                css_class='form-row'
            )
        )
