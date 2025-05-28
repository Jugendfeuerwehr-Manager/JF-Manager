from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.generic import FormView
from django.utils.decorators import method_decorator
from datetime import timedelta
from .models import NotificationPreference, NotificationLog, EmailTemplate, Order, OrderStatus
from .forms_notifications import NotificationPreferenceForm, AdminNotificationDashboardFilterForm
from .forms import OrderSummaryForm
from .notifications import OrderNotificationService


@login_required
def notification_preferences(request):
    """View for users to manage their notification preferences"""
    # Get or create notification preferences for the user
    prefs, created = NotificationPreference.objects.get_or_create(
        user=request.user,
        defaults={
            'email_new_orders': True,
            'email_status_updates': True,
            'email_bulk_updates': False,
            'email_pending_reminders': False,
        }
    )
    
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=prefs, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ihre Benachrichtigungseinstellungen wurden erfolgreich gespeichert.')
            return redirect('orders:notification_preferences')
    else:
        form = NotificationPreferenceForm(instance=prefs, user=request.user)
    
    return render(request, 'orders/notification_preferences.html', {
        'form': form,
        'preferences': prefs,
        'created': created,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_notification_dashboard(request):
    """Admin dashboard for monitoring notifications"""
    # Apply filters
    filter_form = AdminNotificationDashboardFilterForm(request.GET or None)
    
    queryset = NotificationLog.objects.all()
    
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('notification_type'):
            queryset = queryset.filter(notification_type=filter_form.cleaned_data['notification_type'])
        
        if filter_form.cleaned_data.get('status'):
            queryset = queryset.filter(status=filter_form.cleaned_data['status'])
        
        if filter_form.cleaned_data.get('date_from'):
            queryset = queryset.filter(created_at__date__gte=filter_form.cleaned_data['date_from'])
        
        if filter_form.cleaned_data.get('date_to'):
            queryset = queryset.filter(created_at__date__lte=filter_form.cleaned_data['date_to'])
        
        if filter_form.cleaned_data.get('recipient_email'):
            queryset = queryset.filter(recipient_email__icontains=filter_form.cleaned_data['recipient_email'])
    
    # Pagination
    paginator = Paginator(queryset.order_by('-created_at'), 25)
    page_number = request.GET.get('page')
    notifications = paginator.get_page(page_number)
    
    # Statistics
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    stats = {
        'total_notifications': NotificationLog.objects.count(),
        'sent_today': NotificationLog.objects.filter(sent_at__date=today).count(),
        'failed_today': NotificationLog.objects.filter(status='failed', created_at__date=today).count(),
        'pending_count': NotificationLog.objects.filter(status='pending').count(),
        'week_stats': NotificationLog.objects.filter(created_at__gte=week_ago).aggregate(
            total=Count('id'),
            sent=Count('id', filter=Q(status='sent')),
            failed=Count('id', filter=Q(status='failed'))
        ),
        'month_stats': NotificationLog.objects.filter(created_at__gte=month_ago).aggregate(
            total=Count('id'),
            sent=Count('id', filter=Q(status='sent')),
            failed=Count('id', filter=Q(status='failed'))
        )
    }
    
    # Recent failed notifications
    recent_failed = NotificationLog.objects.filter(
        status='failed',
        created_at__gte=week_ago
    ).order_by('-created_at')[:10]
    
    return render(request, 'orders/admin_notification_dashboard.html', {
        'filter_form': filter_form,
        'notifications': notifications,
        'stats': stats,
        'recent_failed': recent_failed,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def notification_detail(request, log_id):
    """Detailed view of a specific notification"""
    notification = get_object_or_404(NotificationLog, id=log_id)
    
    return render(request, 'orders/notification_detail.html', {
        'notification': notification,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def retry_failed_notification(request, log_id):
    """Retry sending a failed notification"""
    if request.method == 'POST':
        notification = get_object_or_404(NotificationLog, id=log_id, status='failed')
        
        # Here you would implement logic to retry sending the notification
        # For now, we'll just mark it as pending
        notification.status = 'pending'
        notification.error_message = ''
        notification.save()
        
        messages.success(request, f'Benachrichtigung #{notification.id} wurde zum erneuten Versand markiert.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
    
    return redirect('orders:admin_notification_dashboard')


@login_required
@user_passes_test(lambda u: u.is_staff)
def email_template_list(request):
    """List and manage email templates"""
    templates = EmailTemplate.objects.all().order_by('template_type')
    
    # Group templates by type for easier management
    template_groups = {}
    for template in templates:
        if template.template_type not in template_groups:
            template_groups[template.template_type] = []
        template_groups[template.template_type].append(template)
    
    return render(request, 'orders/email_template_list.html', {
        'templates': templates,
        'template_groups': template_groups,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def notification_stats_api(request):
    """API endpoint for notification statistics (for charts/dashboard)"""
    days = int(request.GET.get('days', 7))
    now = timezone.now()
    start_date = now - timedelta(days=days)
    
    # Daily statistics
    daily_stats = []
    for i in range(days):
        date = (start_date + timedelta(days=i)).date()
        day_stats = NotificationLog.objects.filter(created_at__date=date).aggregate(
            total=Count('id'),
            sent=Count('id', filter=Q(status='sent')),
            failed=Count('id', filter=Q(status='failed')),
            pending=Count('id', filter=Q(status='pending'))
        )
        daily_stats.append({
            'date': date.isoformat(),
            'total': day_stats['total'],
            'sent': day_stats['sent'],
            'failed': day_stats['failed'],
            'pending': day_stats['pending']
        })
    
    # Type breakdown
    type_stats = list(NotificationLog.objects.filter(
        created_at__gte=start_date
    ).values('notification_type').annotate(
        count=Count('id')
    ).order_by('-count'))
    
    return JsonResponse({
        'daily_stats': daily_stats,
        'type_stats': type_stats,
        'period': f'{days} Tage'
    })


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(lambda u: u.is_staff), name='dispatch')
class OrderSummaryView(FormView):
    """View for sending order summaries to external personnel"""
    template_name = 'orders/order_summary.html'
    form_class = OrderSummaryForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get preview data for display
        orders = Order.objects.all().order_by('-order_date')[:10]  # Last 10 orders for preview
        context['preview_orders'] = orders
        context['total_orders'] = Order.objects.count()
        
        # Status statistics
        status_stats = OrderStatus.objects.filter(is_active=True).annotate(
            order_count=Count('orderitem__order', distinct=True)
        )
        context['status_stats'] = status_stats
        
        return context
    
    def form_valid(self, form):
        recipient_email = form.cleaned_data['recipient_email']
        status_filter = form.cleaned_data['status_filter']
        date_from = form.cleaned_data['date_from']
        date_to = form.cleaned_data['date_to']
        include_notes = form.cleaned_data['include_notes']
        group_by_category = form.cleaned_data['group_by_category']
        additional_notes = form.cleaned_data['additional_notes']
        
        # Build queryset based on filters
        orders_queryset = Order.objects.all()
        
        # Apply date filters
        if date_from:
            orders_queryset = orders_queryset.filter(order_date__date__gte=date_from)
        if date_to:
            orders_queryset = orders_queryset.filter(order_date__date__lte=date_to)
        
        # Apply status filter
        if status_filter:
            orders_queryset = orders_queryset.filter(items__status__in=status_filter).distinct()
        
        orders_queryset = orders_queryset.order_by('-order_date')
        
        # Prepare filter context for email template
        filters = {
            'date_from': date_from,
            'date_to': date_to,
            'status_filter': status_filter,
            'include_notes': include_notes,
            'group_by_category': group_by_category,
            'additional_notes': additional_notes,
        }
        
        try:
            # Send the order summary email
            success = OrderNotificationService.send_order_summary_notification(
                recipient_email=recipient_email,
                orders=orders_queryset,
                filters=filters,
                request=self.request
            )
            
            if success:
                messages.success(
                    self.request,
                    f'Bestellübersicht wurde erfolgreich an {recipient_email} gesendet. '
                    f'({orders_queryset.count()} Bestellungen)'
                )
            else:
                messages.error(
                    self.request,
                    'Fehler beim Versenden der Bestellübersicht. Bitte versuchen Sie es erneut.'
                )
                
        except Exception as e:
            messages.error(
                self.request,
                f'Fehler beim Versenden der E-Mail: {str(e)}'
            )
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return self.request.path  # Stay on the same page
