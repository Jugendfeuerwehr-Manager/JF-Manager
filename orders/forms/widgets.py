from django import forms


class Select2Widget(forms.Select):
    """Custom Select2 widget for searchable dropdowns"""
    
    def __init__(self, attrs=None, choices=()):
        default_attrs = {
            'class': 'form-control select2-widget',
            'data-allow-clear': 'true',
            'data-placeholder': 'Suchen...'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs, choices)
    
    class Media:
        css = {
            'all': ('css/select2-custom.css',)
        }
        js = ('js/select2-init.js',)
