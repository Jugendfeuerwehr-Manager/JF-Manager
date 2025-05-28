from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.template import Template, Context
from django.conf import settings
from django.utils.html import strip_tags
from django.urls import reverse
from django.utils import timezone
from collections import defaultdict
from members.models import Member
from users.models import CustomUser
from .models import Order, OrderItem, OrderStatus, NotificationLog, EmailTemplate


class OrderNotificationService:
    """Enhanced service for sending order-related email notifications with logging"""
    
    @staticmethod
    def _get_email_template(template_type):
        """Get custom email template if available, otherwise use default"""
        try:
            return EmailTemplate.objects.get(template_type=template_type, is_active=True)
        except EmailTemplate.DoesNotExist:
            return None
    
    @staticmethod
    def _render_template(template_content, context):
        """Render Django template with context"""
        template = Template(template_content)
        return template.render(Context(context))
    
    @staticmethod
    def _log_notification(notification_type, recipient_email, subject, order=None, order_item=None):
        """Create a notification log entry"""
        return NotificationLog.objects.create(
            notification_type=notification_type,
            recipient_email=recipient_email,
            subject=subject,
            order=order,
            order_item=order_item,
            status='pending'
        )
    
    @staticmethod
    def _check_user_preferences(user, notification_type):
        """Check if user wants to receive this type of notification"""
        try:
            prefs = user.notification_preferences
            preference_map = {
                'order_created': prefs.email_new_orders,
                'status_update': prefs.email_status_updates,
                'bulk_update': prefs.email_bulk_updates,
                'pending_reminder': prefs.email_pending_reminders,
            }
            return preference_map.get(notification_type, True)  # Default to True if not specified
        except:
            return True  # Default to sending if no preferences exist
    
    @staticmethod
    def send_order_created_notification(order, request=None):
        """Send notification when new order is created"""
        try:
            # Get site domain for absolute URLs
            if request:
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
            else:
                domain = 'localhost:8000'  # Default for development
                protocol = 'http'
            
            # Prepare context for template
            context = {
                'order': order,
                'member': order.member,
                'domain': domain,
                'protocol': protocol,
                'order_url': f"{protocol}://{domain}{reverse('orders:detail', kwargs={'pk': order.pk})}",
                'items': order.items.all()
            }
            
            # Try to get custom email template
            email_template = OrderNotificationService._get_email_template('order_created')
            
            if email_template:
                # Use custom template
                subject = OrderNotificationService._render_template(email_template.subject_template, context)
                html_message = OrderNotificationService._render_template(email_template.html_template, context)
                plain_message = OrderNotificationService._render_template(email_template.text_template, context) if email_template.text_template else strip_tags(html_message)
            else:
                # Use default template
                subject = f'Neue Bestellung #{order.pk} für {order.member.get_full_name()}'
                html_message = render_to_string('orders/emails/order_created.html', context)
                plain_message = strip_tags(html_message)
            
            # Send to administrators
            admin_users = CustomUser.objects.filter(is_staff=True, email__isnull=False).exclude(email='')
            
            success_count = 0
            for admin_user in admin_users:
                # Check user preferences
                if not OrderNotificationService._check_user_preferences(admin_user, 'order_created'):
                    continue
                
                # Create log entry
                log_entry = OrderNotificationService._log_notification(
                    'order_created', admin_user.email, subject, order
                )
                
                try:
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[admin_user.email],
                        fail_silently=False,
                    )
                    log_entry.mark_as_sent()
                    success_count += 1
                except Exception as e:
                    log_entry.mark_as_failed(str(e))
                
            return success_count > 0
            
        except Exception as e:
            # Log error but don't fail order creation
            print(f"Failed to send order created notification: {e}")
            return False
    
    @staticmethod
    def send_status_update_notification(order_item, old_status, new_status, updated_by, request=None):
        """Send notification when order item status changes"""
        try:
            # Get site domain for absolute URLs
            if request:
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
            else:
                domain = 'localhost:8000'  # Default for development
                protocol = 'http'
            
            # Prepare context for template
            context = {
                'order_item': order_item,
                'order': order_item.order,
                'member': order_item.order.member,
                'old_status': old_status,
                'new_status': new_status,
                'updated_by': updated_by,
                'domain': domain,
                'protocol': protocol,
                'order_url': f"{protocol}://{domain}{reverse('orders:detail', kwargs={'pk': order_item.order.pk})}",
            }
            
            # Render email templates
            subject = f'Status-Update: {order_item.item.name} für {order_item.order.member.get_full_name()}'
            html_message = render_to_string('orders/emails/status_update.html', context)
            plain_message = strip_tags(html_message)
            
            # Collect recipients
            recipients = []
            
            # Send to member if they have an email
            if hasattr(order_item.order.member, 'email') and order_item.order.member.email:
                recipients.append(order_item.order.member.email)
            
            # Also send to order creator if different from member
            if order_item.order.ordered_by and order_item.order.ordered_by.email:
                if order_item.order.ordered_by.email not in recipients:
                    # Check user preferences
                    if OrderNotificationService._check_user_preferences(order_item.order.ordered_by, 'status_update'):
                        recipients.append(order_item.order.ordered_by.email)
            
            success_count = 0
            for recipient_email in recipients:
                # Create log entry
                log_entry = OrderNotificationService._log_notification(
                    'status_update', recipient_email, subject, order_item.order, order_item
                )
                
                try:
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient_email],
                        fail_silently=False,
                    )
                    log_entry.mark_as_sent()
                    success_count += 1
                except Exception as e:
                    log_entry.mark_as_failed(str(e))
                
            return success_count > 0
            
        except Exception as e:
            # Log error but don't fail status update
            print(f"Failed to send status update notification: {e}")
            return False
    
    @staticmethod
    def send_bulk_status_update_notification(order_items, new_status, updated_by, request=None):
        """Send notification for bulk status updates"""
        try:
            # Group items by order
            orders_dict = {}
            for item in order_items:
                if item.order.pk not in orders_dict:
                    orders_dict[item.order.pk] = {
                        'order': item.order,
                        'items': []
                    }
                orders_dict[item.order.pk]['items'].append(item)
            
            # Get site domain for absolute URLs
            if request:
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
            else:
                domain = 'localhost:8000'  # Default for development
                protocol = 'http'
            
            # Send notification for each order
            for order_data in orders_dict.values():
                context = {
                    'order': order_data['order'],
                    'items': order_data['items'],
                    'member': order_data['order'].member,
                    'new_status': new_status,
                    'updated_by': updated_by,
                    'domain': domain,
                    'protocol': protocol,
                    'order_url': f"{protocol}://{domain}{reverse('orders:detail', kwargs={'pk': order_data['order'].pk})}",
                }
                
                # Render email templates
                subject = f'Bulk Status-Update für Bestellung #{order_data["order"].pk}'
                html_message = render_to_string('orders/emails/bulk_status_update.html', context)
                plain_message = strip_tags(html_message)
                
                # Send to member if they have an email
                recipient_list = []
                if hasattr(order_data['order'].member, 'email') and order_data['order'].member.email:
                    recipient_list.append(order_data['order'].member.email)
                
                # Also send to order creator if different from member
                if order_data['order'].ordered_by and order_data['order'].ordered_by.email:
                    if order_data['order'].ordered_by.email not in recipient_list:
                        recipient_list.append(order_data['order'].ordered_by.email)
                
                if recipient_list:
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=recipient_list,
                        fail_silently=False,
                    )
                    
            return True
            
        except Exception as e:
            # Log error but don't fail bulk update
            print(f"Failed to send bulk status update notification: {e}")
            return False
    
    @staticmethod
    def send_pending_order_reminder(order, pending_items, request=None):
        """Send reminder notification for pending order items"""
        try:
            # Get site domain for absolute URLs
            if request:
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
            else:
                domain = 'localhost:8000'
                protocol = 'http'
            
            # Prepare context for template
            context = {
                'order': order,
                'pending_items': pending_items,
                'member': order.member,
                'domain': domain,
                'protocol': protocol,
                'order_url': f"{protocol}://{domain}{reverse('orders:detail', kwargs={'pk': order.pk})}",
            }
            
            # Render email templates
            subject = f'Erinnerung: Offene Bestellartikel in Bestellung #{order.pk}'
            html_message = render_to_string('orders/emails/pending_reminder.html', context)
            plain_message = strip_tags(html_message)
            
            # Send to administrators
            admin_users = CustomUser.objects.filter(is_staff=True, email__isnull=False).exclude(email='')
            admin_emails = [user.email for user in admin_users]
            
            if admin_emails:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    html_message=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=False,
                )
                
            return True
            
        except Exception as e:
            # Log error but don't fail the process
            print(f"Failed to send pending order reminder: {e}")
            return False
    
    @staticmethod
    def send_order_summary_notification(recipient_email, orders, filters=None, request=None):
        """Send order summary notification to external personnel (e.g., Gerätewart)"""
        try:
            # Get site domain for absolute URLs
            if request:
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
            else:
                domain = 'localhost:8000'
                protocol = 'http'
            
            # Prepare grouped data for template
            grouped_items = defaultdict(list)
            shopping_list = defaultdict(lambda: {
                'item_name': '',
                'category': '',
                'sizes': defaultdict(int),
                'total_quantity': 0,
                'statuses': set(),
                'order_items': []
            })
            
            total_items = 0
            
            # Process all order items
            for order in orders:
                for item in order.items.all():
                    total_items += item.quantity
                    
                    # Group by category if requested
                    category = item.item.category or 'Keine Kategorie'
                    
                    # Find existing item data in grouped_items
                    item_found = False
                    for existing_item in grouped_items[category]:
                        if existing_item['item'] == item.item:
                            existing_item['order_items'].append(item)
                            existing_item['total_quantity'] += item.quantity
                            item_found = True
                            break
                    
                    if not item_found:
                        grouped_items[category].append({
                            'item': item.item,
                            'order_items': [item],
                            'total_quantity': item.quantity
                        })
                    
                    # Build shopping list summary
                    item_key = f"{item.item.name}_{item.item.category}"
                    shopping_item = shopping_list[item_key]
                    shopping_item['item_name'] = item.item.name
                    shopping_item['category'] = item.item.category
                    shopping_item['total_quantity'] += item.quantity
                    shopping_item['statuses'].add(item.status.name)
                    shopping_item['order_items'].append(item)
                    
                    size_key = item.size if item.size else 'Keine'
                    shopping_item['sizes'][size_key] += item.quantity
            
            # Convert shopping_list to list for template
            shopping_list_final = []
            for item_data in shopping_list.values():
                item_data['statuses'] = list(item_data['statuses'])
                shopping_list_final.append(item_data)
            
            # Sort shopping list by category then name
            shopping_list_final.sort(key=lambda x: (x['category'] or 'ZZZ', x['item_name']))
            
            # Prepare context for template
            context = {
                'orders': orders,
                'grouped_items': dict(grouped_items),
                'shopping_list': shopping_list_final,
                'total_items': total_items,
                'domain': domain,
                'protocol': protocol,
                'date_from': filters.get('date_from') if filters else None,
                'date_to': filters.get('date_to') if filters else None,
                'status_filter': list(filters.get('status_filter', [])) if filters and filters.get('status_filter') else None,
                'include_notes': filters.get('include_notes', True) if filters else True,
                'group_by_category': filters.get('group_by_category', True) if filters else True,
                'additional_notes': filters.get('additional_notes', '') if filters else '',
            }
            
            # Render email templates
            subject = f'Bestellübersicht JF-Manager - {orders.count()} Bestellungen ({total_items} Artikel)'
            html_message = render_to_string('orders/emails/order_summary.html', context)
            plain_message = strip_tags(html_message)
            
            # Create log entry
            log_entry = OrderNotificationService._log_notification(
                'order_summary', recipient_email, subject
            )
            
            try:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    html_message=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
                log_entry.mark_as_sent()
                return True
            except Exception as e:
                log_entry.mark_as_failed(str(e))
                raise e
                
        except Exception as e:
            print(f"Failed to send order summary notification: {e}")
            return False


class OrderWorkflowService:
    """Service for handling order status workflows"""
    
    @staticmethod
    def get_available_transitions(current_status):
        """Get available status transitions from current status"""
        # Define workflow transitions
        transitions = {
            'pending': ['ordered', 'cancelled'],
            'ordered': ['received', 'cancelled'],
            'received': ['ready', 'defective'],
            'ready': ['delivered'],
            'delivered': [],  # Final state
            'cancelled': [],  # Final state
            'defective': ['ordered', 'cancelled'],
            'ORDERED': ['RECEIVED', 'CANCELLED'],  # Can reorder or cancel
            'RECEIVED': ['DELIVERED', 'CANCELLED'],  # Can reorder or cancel
        }
        
        return transitions.get(current_status.code, [])
    
    @staticmethod
    def can_transition_to(current_status, target_status):
        """Check if transition from current to target status is allowed"""
        available_transitions = OrderWorkflowService.get_available_transitions(current_status)
        return target_status.code in available_transitions
    
    @staticmethod
    def get_next_statuses(current_status):
        """Get OrderStatus objects for next possible statuses"""
        available_codes = OrderWorkflowService.get_available_transitions(current_status)
        return OrderStatus.objects.filter(code__in=available_codes, is_active=True)
