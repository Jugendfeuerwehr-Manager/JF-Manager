from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from ..models import OrderItem


class OrderStatusUpdateForm(forms.ModelForm):
    """Form für Status-Updates von Bestellartikeln"""
    
    class Meta:
        model = OrderItem
        fields = ['status', 'received_date', 'delivered_date', 'notes']
        widgets = {
            'received_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'delivered_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'status',
            Row(
                Column('received_date', css_class='form-group col-md-6 mb-0'),
                Column('delivered_date', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'notes',
            Submit('submit', 'Status aktualisieren', css_class='btn btn-primary'),
        )
