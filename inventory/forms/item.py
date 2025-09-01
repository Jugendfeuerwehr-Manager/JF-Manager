from django import forms
from ..models import Item


class DynamicItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'category', 'base_unit', 'is_variant_parent', 'attributes']
        widgets = {'attributes': forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'attributes':
                if isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs.update({'class': 'form-check-input'})
                else:
                    field.widget.attrs.update({'class': 'form-control'})
        self.fields['category'].widget.attrs.update({'onchange': 'handleCategoryChange(this.value)'})

    def clean_attributes(self):
        attrs = self.cleaned_data.get('attributes') or {}
        category = self.cleaned_data.get('category')
        if category and category.schema:
            schema = category.schema
            for fname, ftype in schema.items():
                if fname in attrs and ftype == 'number':
                    val = attrs[fname]
                    if not isinstance(val, (int, float)):
                        try:
                            attrs[fname] = float(val)
                        except (ValueError, TypeError):
                            raise forms.ValidationError(f'{fname} muss eine Zahl sein.')
        return attrs

ItemForm = DynamicItemForm
