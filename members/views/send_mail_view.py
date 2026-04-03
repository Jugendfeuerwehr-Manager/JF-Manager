import os
import smtplib

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.mail import EmailMessage
from django.shortcuts import redirect
from django.views.generic import FormView

from members.forms import SendMailForm
from members.models import Member

# Mapping of allowed file extensions to their MIME types for content-type validation.
_ALLOWED_MIME_TYPES: dict[str, str] = {
    'pdf':  'application/pdf',
    'doc':  'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'jpg':  'image/jpeg',
    'jpeg': 'image/jpeg',
    'png':  'image/png',
    'gif':  'image/gif',
}


def _safe_attachment_name(name: str) -> str:
    """Return a safe filename stripped of any directory components."""
    return os.path.basename(name)


def _safe_content_type(filename: str, declared_content_type: str) -> str:
    """Return a validated MIME type based on the file extension.

    If the declared content type doesn't match the expected type for the
    file extension, fall back to the extension-based type to prevent a
    caller from injecting a misleading content type.
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    expected = _ALLOWED_MIME_TYPES.get(ext)
    if expected:
        return expected
    # Unknown extension – use the declared type but strip parameters to be safe.
    return declared_content_type.split(';')[0].strip() or 'application/octet-stream'


class SendMailView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    View for composing and sending emails to one or more members.
    Supports file attachments uploaded via drag-and-drop or file picker.
    The body field is pre-filled with the signature from the global email
    settings so that the signature is part of the message and is never
    appended a second time server-side.
    """

    template_name = 'send_mail.html'
    permission_required = 'members.view_member'

    def get_form_class(self):
        return SendMailForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pre-select recipients from query-string ?member=<pk>&member=<pk>
        kwargs['initial_members'] = self._get_preselected_members()
        return kwargs

    def _get_preselected_members(self):
        pks = self.request.GET.getlist('member')
        if pks:
            return Member.objects.filter(pk__in=pks)
        return Member.objects.none()

    def form_valid(self, form):
        recipients = form.cleaned_data['recipients']
        subject = form.cleaned_data['subject']
        # body already contains the signature as typed/pre-filled by the user
        body = form.cleaned_data['body']
        attachments = self.request.FILES.getlist('attachments')

        recipient_emails = [m.email for m in recipients if m.email]

        if not recipient_emails:
            messages.error(self.request, 'Keiner der ausgewählten Empfänger hat eine E-Mail-Adresse hinterlegt.')
            return self.form_invalid(form)

        try:
            from django.conf import settings as django_settings
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to=recipient_emails,
            )

            for attachment in attachments:
                safe_name = _safe_attachment_name(attachment.name)
                safe_ct = _safe_content_type(safe_name, attachment.content_type)
                email.attach(safe_name, attachment.read(), safe_ct)

            email.send(fail_silently=False)

            messages.success(
                self.request,
                f'E-Mail wurde erfolgreich an {len(recipient_emails)} Empfänger gesendet.'
            )
        except (smtplib.SMTPException, OSError, ValueError) as exc:
            messages.error(self.request, f'Fehler beim Senden der E-Mail: {exc}')
            return self.form_invalid(form)

        return redirect('members:index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_members'] = Member.objects.filter(email__isnull=False).exclude(email='').order_by('lastname', 'name')
        return context
