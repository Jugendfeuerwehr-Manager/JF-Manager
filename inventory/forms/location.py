from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, Row, Column
from crispy_forms.bootstrap import FormActions
from django import forms

from ..models import StorageLocation


class StorageLocationForm(forms.ModelForm):
    class Meta:
        model = StorageLocation
        fields = ['name', 'parent', 'is_member', 'member']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'is_member':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        self.fields['parent'].help_text = 'Übergeordneter Lagerort (optional)'
        self.fields['is_member'].help_text = 'Aktivieren für Mitglied-Lagerorte'
        self.fields['member'].help_text = 'Nur wählen wenn Mitglied-Lagerort'
        if self.instance.pk:
            self.fields['parent'].queryset = StorageLocation.objects.exclude(pk=self.instance.pk)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Lagerort Details',
                Row(Column('name', css_class='form-group col-md-12 mb-0'), css_class='form-row'),
                Row(Column('parent', css_class='form-group col-md-12 mb-0'), css_class='form-row'),
                Row(Column('is_member', css_class='form-group col-md-6 mb-0'), Column('member', css_class='form-group col-md-6 mb-0'), css_class='form-row'),
            ),
            FormActions(Submit('submit', 'Speichern', css_class='btn btn-primary'))
        )

    def clean(self):
        cleaned = super().clean()
        is_member = cleaned.get('is_member')
        member = cleaned.get('member')
        parent = cleaned.get('parent')
        if is_member and not member:
            raise forms.ValidationError('Mitglied auswählen wenn "Ist Mitglied" aktiviert ist.')
        if not is_member and member:
            raise forms.ValidationError('"Ist Mitglied" aktivieren wenn ein Mitglied gewählt ist.')
        if parent and self.instance.pk:
            current = parent
            while current:
                if current.pk == self.instance.pk:
                    raise forms.ValidationError('Zyklische Referenz nicht erlaubt.')
                current = current.parent
        return cleaned
