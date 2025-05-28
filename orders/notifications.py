from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.urls import reverse
from members.models import Member
from users.models import CustomUser
from .models import Order, OrderItem, OrderStatus


class OrderNotificationService:
    """Service for sending order-related email notifications"""
    
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
            
            # Render email templates
            subject = f'Neue Bestellung #{order.pk} für {order.member.get_full_name()}'
            html_message = render_to_string('orders/emails/order_created.html', context)
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
            
            # Send to member if they have an email
            recipient_list = []
            if hasattr(order_item.order.member, 'email') and order_item.order.member.email:
                recipient_list.append(order_item.order.member.email)
            
            # Also send to order creator if different from member
            if order_item.order.ordered_by and order_item.order.ordered_by.email:
                if order_item.order.ordered_by.email not in recipient_list:
                    recipient_list.append(order_item.order.ordered_by.email)
            
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
            'defective': ['ordered', 'cancelled'],  # Can reorder or cancel
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
