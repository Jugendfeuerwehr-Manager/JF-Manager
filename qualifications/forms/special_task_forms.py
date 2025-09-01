from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Field, Row, Column
from datetime import date

from ..models import SpecialTaskType, SpecialTask


class SpecialTaskTypeForm(forms.ModelForm):
    class Meta:
        model = SpecialTaskType
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'name',
            'description',
            Submit('submit', 'Speichern', css_class='btn btn-primary'),
        )


class SpecialTaskForm(forms.ModelForm):
    class Meta:
        model = SpecialTask
        fields = ['task', 'user', 'member', 'start_date', 'end_date', 'note']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
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
            'task',
            Row(
                Column('user', css_class='form-group col-md-6 mb-0'),
                Column('member', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('start_date', css_class='form-group col-md-6 mb-0'),
                Column('end_date', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'note',
            Submit('submit', 'Speichern', css_class='btn btn-primary'),
        )

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        member = cleaned_data.get('member')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        # Mindestens User oder Member
        if not user and not member:
            raise ValidationError('Entweder Benutzer oder Mitglied muss ausgewählt werden.')
        
        # Nicht beide gleichzeitig
        if user and member:
            raise ValidationError('Nur Benutzer oder Mitglied kann ausgewählt werden, nicht beide.')

        # Enddatum nicht vor Startdatum
        if end_date and start_date and end_date < start_date:
            raise ValidationError({'end_date': 'Enddatum kann nicht vor Startdatum liegen.'})

        return cleaned_data


class SpecialTaskFilterForm(forms.Form):
    """Filter-Form für die Sonderaufgaben-Übersicht"""
    
    STATUS_CHOICES = [
        ('', 'Alle'),
        ('active', 'Aktiv'),
        ('completed', 'Beendet'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label='Status'
    )
    task_type = forms.ModelChoiceField(
        queryset=SpecialTaskType.objects.all(),
        required=False,
        empty_label='Alle Aufgaben',
        label='Aufgabentyp'
    )
    search = forms.CharField(
        max_length=100,
        required=False,
        label='Suche',
        widget=forms.TextInput(attrs={'placeholder': 'Name, Aufgabe...'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'mb-4'
        self.helper.layout = Layout(
            Row(
                Column('status', css_class='form-group col-md-3 mb-0'),
                Column('task_type', css_class='form-group col-md-3 mb-0'),
                Column('search', css_class='form-group col-md-4 mb-0'),
                Column(
                    Submit('filter', 'Filtern', css_class='btn btn-primary'),
                    css_class='form-group col-md-2 mb-0 d-flex align-items-end'
                ),
                css_class='form-row'
            )
        )


class SpecialTaskEndForm(forms.Form):
    """Form zum Beenden einer Sonderaufgabe"""
    
    end_date = forms.DateField(
        label='Enddatum',
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=date.today
    )
    note = forms.CharField(
        label='Abschlussnotiz',
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text='Optionale Notiz zum Abschluss der Aufgabe'
    )

    def __init__(self, *args, **kwargs):
        self.special_task = kwargs.pop('special_task', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'end_date',
            'note',
            Submit('submit', 'Aufgabe beenden', css_class='btn btn-warning'),
        )

    def clean_end_date(self):
        end_date = self.cleaned_data['end_date']
        
        if self.special_task and end_date < self.special_task.start_date:
            raise ValidationError('Enddatum kann nicht vor Startdatum liegen.')
        
        return end_date
