from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Row, Column, Div, Button
from django import forms
from bootstrap_datepicker_plus.widgets import DateTimePickerInput

from .models import Service


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = '__all__'
        exclude = ['attendees']
        widgets = {
            'start': DateTimePickerInput(format='%d.%m.%Y %H:%M'),
            'end': DateTimePickerInput(format='%d.%m.%Y %H:%M')
        }

    def __init__(self, *args, **kwargs):
        super(ServiceForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = ''
        self.helper.label_class = 'form-label'
        
        # Add some styling to form fields
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'rounded-2'
            })
            
        self.helper.layout = Layout(
            Row(
                Column('start', css_class='col-md-4 mb-4'),
                Column('end', css_class='col-md-4 mb-4'),
                Column(
                    Button('set-time-btn', 'Standard', css_id="set-time-btn", css_class='btn btn-secondary'),
                    css_class='align-content-center'
                ),
                
            ),
            Row(
                Column('place', css_class='col-md-12 mb-4'),
            ),
            Row(
                Column('operations_manager', css_class='col-md-12 mb-4'),
            ),
            Row(
                Column('topic', css_class='col-md-12 mb-4'),
            ),
            Row(
                Column('description', css_class='col-md-12 mb-4'),
            ),
            Row(
                Column('events', css_class='col-md-12 mb-4'),
            ),
            Row(
                Column(
                    Div(
                        Submit('submit', 'Speichern', css_class='btn btn-primary me-2'),
                        Submit('cancel', 'Abbrechen', css_class='btn btn-light'),
                        css_class='d-flex justify-content-end'
                    ),
                    css_class='col-12'
                )
            )
        )