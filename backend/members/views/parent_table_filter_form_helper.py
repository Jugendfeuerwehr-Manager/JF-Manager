import crispy_forms
from crispy_forms.layout import Layout, Submit


class ParentTableFilterFormHelper(crispy_forms.helper.FormHelper):
    form_method = 'GET'
    form_class = 'form-inline'
    layout = Layout(
        'name__contains',
        'lastname__contains',
        Submit('submit', 'Filtern')

    )