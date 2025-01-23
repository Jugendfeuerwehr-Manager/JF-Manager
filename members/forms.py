from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, ButtonHolder, Row, Column, Div
from django import forms
from bootstrap_datepicker_plus.widgets import DatePickerInput
from .models import Member, Parent, EventType
import django_filters


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
