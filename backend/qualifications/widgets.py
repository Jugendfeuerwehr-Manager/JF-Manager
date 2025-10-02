from django import forms
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe


class Select2Widget(forms.Select):
    """Custom Select2 Widget für bessere Benutzerauswahl"""
    
    def __init__(self, attrs=None, choices=(), url=None, placeholder="Auswählen..."):
        self.url = url
        self.placeholder = placeholder
        super().__init__(attrs, choices)

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        attrs.setdefault('class', '')
        attrs['class'] += ' select2-widget'
        attrs['data-placeholder'] = self.placeholder
        if self.url:
            attrs['data-ajax-url'] = self.url
        return attrs

    class Media:
        css = {
            'all': ('https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',)
        }
        js = (
            'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',
            'js/select2-init.js',
        )


class UserSelect2Widget(Select2Widget):
    """Select2 Widget speziell für User-Auswahl"""
    
    def __init__(self, attrs=None, choices=()):
        super().__init__(
            attrs=attrs, 
            choices=choices,
            url=reverse_lazy('qualifications:user_autocomplete'),
            placeholder="Benutzer auswählen..."
        )


class MemberSelect2Widget(Select2Widget):
    """Select2 Widget speziell für Member-Auswahl"""
    
    def __init__(self, attrs=None, choices=()):
        super().__init__(
            attrs=attrs, 
            choices=choices,
            url=reverse_lazy('qualifications:member_autocomplete'),
            placeholder="Mitglied auswählen..."
        )
