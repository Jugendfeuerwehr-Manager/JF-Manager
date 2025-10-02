from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse, Http404, FileResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from guardian.decorators import permission_required_or_403
import json

from ..models import Qualification, SpecialTask
from members.models import Attachment
from ..forms.attachment_forms import AttachmentForm


@login_required
@permission_required_or_403('qualifications.view_qualification')
def qualification_attachment_list(request, qualification_id):
    """List all attachments for a qualification."""
    qualification = get_object_or_404(Qualification, pk=qualification_id)
    attachments = qualification.attachments.all()
    
    return render(request, 'qualifications/attachment_list.html', {
        'qualification': qualification,
        'attachments': attachments
    })


@login_required
@permission_required_or_403('qualifications.change_qualification')
def qualification_attachment_upload(request, qualification_id):
    """Upload a new attachment for a qualification."""
    qualification = get_object_or_404(Qualification, pk=qualification_id)
    
    if request.method == 'POST':
        form = AttachmentForm(request.POST, request.FILES, 
                             content_object=qualification, user=request.user)
        if form.is_valid():
            attachment = form.save()
            messages.success(request, f'Anhang "{attachment.name}" wurde erfolgreich hochgeladen.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'attachment': {
                        'id': attachment.id,
                        'name': attachment.name,
                        'file_url': attachment.get_download_url(),
                        'file_size': attachment.get_file_size_human(),
                        'uploaded_at': attachment.uploaded_at.strftime('%d.%m.%Y %H:%M'),
                    }
                })
            
            return redirect('qualifications:qualification_detail', pk=qualification_id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        form = AttachmentForm(content_object=qualification, user=request.user)
    
    return render(request, 'qualifications/attachment_upload.html', {
        'qualification': qualification,
        'form': form
    })


@login_required
@permission_required_or_403('qualifications.change_qualification')
@require_http_methods(["DELETE"])
def qualification_attachment_delete(request, qualification_id, attachment_id):
    """Delete an attachment from a qualification."""
    qualification = get_object_or_404(Qualification, pk=qualification_id)
    attachment = get_object_or_404(Attachment, pk=attachment_id, 
                                  content_type=ContentType.objects.get_for_model(Qualification),
                                  object_id=qualification_id)
    
    attachment_name = attachment.name
    attachment.delete()
    
    messages.success(request, f'Anhang "{attachment_name}" wurde gelöscht.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('qualifications:qualification_detail', pk=qualification_id)


@login_required
def attachment_download(request, attachment_id):
    """Download an attachment file."""
    attachment = get_object_or_404(Attachment, pk=attachment_id)
    
    # Check permissions based on the content object
    content_object = attachment.content_object
    
    if isinstance(content_object, Qualification):
        if not request.user.has_perm('qualifications.view_qualification'):
            raise Http404
    elif isinstance(content_object, SpecialTask):
        if not request.user.has_perm('qualifications.view_specialtask'):
            raise Http404
    
    try:
        response = FileResponse(
            attachment.file.open('rb'),
            as_attachment=True,
            filename=f"{attachment.name}.{attachment.get_file_extension()}"
        )
        return response
    except FileNotFoundError:
        messages.error(request, f'Datei "{attachment.name}" wurde nicht gefunden.')
        raise Http404


# Special Task Attachment Views
@login_required
@permission_required_or_403('qualifications.view_specialtask')
def specialtask_attachment_list(request, specialtask_id):
    """List all attachments for a special task."""
    specialtask = get_object_or_404(SpecialTask, pk=specialtask_id)
    attachments = specialtask.attachments.all()
    
    return render(request, 'qualifications/specialtask_attachment_list.html', {
        'specialtask': specialtask,
        'attachments': attachments
    })


@login_required
@permission_required_or_403('qualifications.change_specialtask')
def specialtask_attachment_upload(request, specialtask_id):
    """Upload a new attachment for a special task."""
    specialtask = get_object_or_404(SpecialTask, pk=specialtask_id)
    
    if request.method == 'POST':
        form = AttachmentForm(request.POST, request.FILES, 
                             content_object=specialtask, user=request.user)
        if form.is_valid():
            attachment = form.save()
            messages.success(request, f'Anhang "{attachment.name}" wurde erfolgreich hochgeladen.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'attachment': {
                        'id': attachment.id,
                        'name': attachment.name,
                        'file_url': attachment.get_download_url(),
                        'file_size': attachment.get_file_size_human(),
                        'uploaded_at': attachment.uploaded_at.strftime('%d.%m.%Y %H:%M'),
                    }
                })
            
            return redirect('qualifications:specialtask_detail', pk=specialtask_id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        form = AttachmentForm(content_object=specialtask, user=request.user)
    
    return render(request, 'qualifications/specialtask_attachment_upload.html', {
        'specialtask': specialtask,
        'form': form
    })


@login_required
@permission_required_or_403('qualifications.change_specialtask')
@require_http_methods(["DELETE"])
def specialtask_attachment_delete(request, specialtask_id, attachment_id):
    """Delete an attachment from a special task."""
    specialtask = get_object_or_404(SpecialTask, pk=specialtask_id)
    attachment = get_object_or_404(Attachment, pk=attachment_id, 
                                  content_type=ContentType.objects.get_for_model(SpecialTask),
                                  object_id=specialtask_id)
    
    attachment_name = attachment.name
    attachment.delete()
    
    messages.success(request, f'Anhang "{attachment_name}" wurde gelöscht.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('qualifications:specialtask_detail', pk=specialtask_id)
