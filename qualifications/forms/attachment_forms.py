from django import forms
from django.contrib.contenttypes.models import ContentType
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Field, HTML
from members.models import Attachment


class AttachmentForm(forms.ModelForm):
    """
    Form for creating and editing attachments.
    """
    class Meta:
        model = Attachment
        fields = ['file', 'name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'z.B. Zertifikat Grundlehrgang'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optionale Beschreibung des Anhangs'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control drag-drop-file',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif',
                'id': 'file-upload'
            })
        }

    def __init__(self, *args, **kwargs):
        self.content_object = kwargs.pop('content_object', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make name required and add help text
        self.fields['name'].required = True
        # Make file field optional
        self.fields['file'].required = False
        self.fields['file'].help_text = 'Zulässige Dateiformate: PDF, DOC, DOCX, JPG, PNG, GIF (max. 10MB) - Optional'
        
        # Setup crispy forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            HTML('''
                <div class="drag-drop-area" id="drag-drop-area">
                    <div class="drag-drop-content">
                        <i class="fas fa-cloud-upload-alt fa-3x text-muted mb-3"></i>
                        <h5>Datei hier ablegen oder klicken zum Auswählen</h5>
                        <p class="text-muted">PDF, DOC, DOCX, JPG, PNG, GIF (max. 10MB)</p>
                    </div>
                </div>
            '''),
            Field('file', css_class='d-none'),
            'name',
            'description',
            Div(
                Submit('submit', 'Anhang hochladen', css_class='btn btn-primary'),
                HTML('<a href="#" onclick="history.back()" class="btn btn-secondary ms-2">Abbrechen</a>'),
                css_class='d-flex gap-2 mt-3'
            ),
        )

    def save(self, commit=True):
        attachment = super().save(commit=False)
        
        if self.content_object:
            attachment.content_object = self.content_object
        
        if self.user:
            attachment.uploaded_by = self.user
        
        # Only save if we have a file or if this is an update to existing attachment
        if commit and (attachment.file or attachment.pk):
            attachment.save()
        
        return attachment


class AttachmentFormSet(forms.BaseInlineFormSet):
    """
    Custom formset for handling multiple attachments.
    """
    def __init__(self, *args, **kwargs):
        self.content_object = kwargs.pop('content_object', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs['content_object'] = self.content_object
        kwargs['user'] = self.user
        return super()._construct_form(i, **kwargs)


# Factory function to create attachment formsets
def attachment_formset_factory(extra=1, can_delete=True):
    """
    Factory function to create attachment formsets.
    """
    return forms.inlineformset_factory(
        parent_model=None,  # Will be set dynamically
        model=Attachment,
        form=AttachmentForm,
        formset=AttachmentFormSet,
        extra=extra,
        can_delete=can_delete,
        fields=['file', 'name', 'description']
    )
