from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from orders.models import Order, OrderStatus, OrderItem
from orders.notifications import OrderNotificationService


class Command(BaseCommand):
    help = 'Send reminder emails for pending order items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Send reminders for orders older than this many days (default: 7)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Don\'t actually send emails, just show what would be sent',
        )

    def handle(self, *args, **options):
        days_threshold = options['days']
        dry_run = options['dry_run']
        
        # Calculate the cutoff date
        cutoff_date = timezone.now() - timedelta(days=days_threshold)
        
        # Find pending status codes (you might need to adjust these based on your status setup)
        pending_status_codes = ['pending', 'ordered']
        pending_statuses = OrderStatus.objects.filter(
            code__in=pending_status_codes,
            is_active=True
        )
        
        # Find orders with pending items older than the threshold
        orders_with_pending = Order.objects.filter(
            order_date__lt=cutoff_date,
            items__status__in=pending_statuses
        ).distinct()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Found {orders_with_pending.count()} orders with pending items older than {days_threshold} days'
            )
        )
        
        emails_sent = 0
        
        for order in orders_with_pending:
            # Get pending items for this order
            pending_items = order.items.filter(status__in=pending_statuses)
            
            if pending_items.exists():
                self.stdout.write(
                    f'Order #{order.pk} for {order.member.get_full_name()} '
                    f'has {pending_items.count()} pending items'
                )
                
                if not dry_run:
                    try:
                        success = OrderNotificationService.send_pending_order_reminder(
                            order, pending_items
                        )
                        if success:
                            emails_sent += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✓ Reminder sent for order #{order.pk}')
                            )
                        else:
                            self.stdout.write(
                                self.style.ERROR(f'  ✗ Failed to send reminder for order #{order.pk}')
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Error sending reminder for order #{order.pk}: {e}')
                        )
                else:
                    self.stdout.write('  (dry run - no email sent)')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'Dry run completed. Would have sent {orders_with_pending.count()} reminder emails.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully sent {emails_sent} reminder emails out of {orders_with_pending.count()} eligible orders.'
                )
            )
