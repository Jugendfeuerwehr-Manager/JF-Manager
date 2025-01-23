from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import Item


class FormActionMixin(object):

    def post(self, request, *args, **kwargs):
        """Add 'Cancel' button redirect."""
        if "cancel" in request.POST:
            url = reverse(self.get_success_url())    # or e.g. reverse(self.get_success_url())
            return HttpResponseRedirect(url)
        else:
            return super(FormActionMixin, self).post(request, *args, **kwargs)


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ('category', 'size', 'identifier1', 'identifier2', 'rented_by')

    def __init__(self, *args, **kwargs):
        super(ItemForm, self).__init__(*args, **kwargs)
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
