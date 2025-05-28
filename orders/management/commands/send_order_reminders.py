from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from orders.models import OrderItem, OrderStatus
from orders.notifications import OrderNotificationService


class Command(BaseCommand):
    help = 'Send reminder notifications for pending orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back for pending orders (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually sending emails'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # Calculate date threshold
        threshold_date = timezone.now() - timedelta(days=days)
        
        # Find pending order items older than threshold
        pending_status = OrderStatus.objects.filter(code='pending').first()
        if not pending_status:
            self.stdout.write(
                self.style.WARNING('No "pending" status found in the system')
            )
            return
        
        pending_items = OrderItem.objects.filter(
            status=pending_status,
            order__order_date__lt=threshold_date
        ).select_related('order', 'order__member', 'order__ordered_by', 'item')
        
        if not pending_items.exists():
            self.stdout.write(
                self.style.SUCCESS(f'No pending orders older than {days} days found')
            )
            return
        
        # Group by order
        orders_dict = {}
        for item in pending_items:
            if item.order.pk not in orders_dict:
                orders_dict[item.order.pk] = {
                    'order': item.order,
                    'items': []
                }
            orders_dict[item.order.pk]['items'].append(item)
        
        sent_count = 0
        error_count = 0
        
        for order_data in orders_dict.values():
            order = order_data['order']
            items = order_data['items']
            
            if dry_run:
                self.stdout.write(
                    f'Would send reminder for Order #{order.pk} with {len(items)} pending items'
                )
            else:
                try:
                    # Send reminder notification
                    success = OrderNotificationService.send_pending_order_reminder(
                        order, items
                    )
                    if success:
                        sent_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Sent reminder for Order #{order.pk}')
                        )
                    else:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'Failed to send reminder for Order #{order.pk}')
                        )
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'Error processing Order #{order.pk}: {e}')
                    )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Dry run completed. Would process {len(orders_dict)} orders.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Sent {sent_count} reminders, {error_count} errors'
                )
            )
