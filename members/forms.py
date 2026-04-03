from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, ButtonHolder, Row, Column, Div
from django import forms
from bootstrap_datepicker_plus.widgets import DatePickerInput
from .models import Member, Parent, EventType
import django_filters

SIGNATURE_SEPARATOR = '\n\n--\n'


class EventForm(forms.Form):
    type = forms.ModelChoiceField(queryset=EventType.objects.all(), required=True, label='Typ')
    date = forms.DateField(
        required=True, 
        label='Datum',
        input_formats=['%Y-%m-%d', '%d.%m.%Y'], 
        widget=DatePickerInput(
            format='%d.%m.%Y',
            options={
                'locale': 'de', 
                'format': 'DD.MM.YYYY'
            }
            )
        )
    notes = forms.CharField(widget=forms.Textarea, label='Bemerkungen', required=False)


    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern'))


class SendMailForm(forms.Form):
    """Form for composing and sending an email to one or more members."""

    recipients = forms.ModelMultipleChoiceField(
        queryset=Member.objects.filter(email__isnull=False).exclude(email='').order_by('lastname', 'name'),
        label='Empfänger',
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )
    subject = forms.CharField(
        label='Betreff',
        max_length=255,
        required=True,
    )
    body = forms.CharField(
        label='Nachricht',
        widget=forms.Textarea(attrs={'rows': 10}),
        required=True,
    )

    def __init__(self, *args, initial_members=None, **kwargs):
        # Load the saved signature and pre-fill the body so the signature is
        # visible to the user while composing. The server-side send code uses
        # the body as-is, which avoids the double-signature problem.
        from dynamic_preferences.registries import global_preferences_registry
        global_preferences = global_preferences_registry.manager()
        signature = global_preferences.get('email__email_signature', '')

        if 'initial' not in kwargs:
            kwargs['initial'] = {}
        if signature and not kwargs['initial'].get('body'):
            kwargs['initial']['body'] = f'{SIGNATURE_SEPARATOR}{signature}'

        super().__init__(*args, **kwargs)

        if initial_members is not None and initial_members.exists():
            self.fields['recipients'].initial = initial_members

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.add_input(Submit('submit', 'E-Mail senden', css_class='btn-primary'))


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = '__all__'


    def __init__(self, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        # Add 'Submit' button
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern'))
        self.helper.add_input(Submit(
            'cancel',
            'Abbrechen',
            css_class='btn-danger',
            formnovalidate='formnovalidate',
        )
        )


class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ParentForm, self).__init__(*args, **kwargs)
        # Add 'Submit' button
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern'))
        self.helper.add_input(Submit(
            'cancel',
            'Abbrechen',
            css_class='btn-danger',
            formnovalidate='formnovalidate',
        )
        )


class MemberFilter(django_filters.FilterSet):
    class Meta:
        model = Member
        fields = ['status', 'group']

class MemberFilterFormHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'get'
        self.form_class = 'filter-form'
        self.form_show_labels = True
        self.html5_required = False
        self.layout = Layout(
            Div(
                Div('status', css_class='form-group filter-status'),
                Div('group', css_class='form-group filter-group'),
                css_class='filter-form-row'
            )
        )
