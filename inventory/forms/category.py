from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, Row, Column
from crispy_forms.bootstrap import FormActions
from django import forms

from ..models import Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'schema']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Kategorie Details',
                Row(Column('name', css_class='form-group col-md-12 mb-0'), css_class='form-row'),
                Row(Column('schema', css_class='form-group col-md-12 mb-0'), css_class='form-row'),
            ),
            FormActions(Submit('submit', 'Speichern', css_class='btn btn-primary'))
        )
        self.fields['schema'].help_text = 'JSON-Schema (z.B. {"größe": "string", "farbe": "string"})'
        if hasattr(self.fields['schema'], 'widget') and hasattr(self.fields['schema'].widget, 'attrs'):
            self.fields['schema'].widget.attrs.update({'rows': 4, 'placeholder': '{"attribut": "string"}'})
