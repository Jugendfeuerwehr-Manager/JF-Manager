"""Management command to clean up duplicate attendance records."""
from django.core.management.base import BaseCommand
from django.db.models import Count
from servicebook.models import Attendance


class Command(BaseCommand):
    help = 'Removes duplicate attendance records, keeping the most recent one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find duplicates
        duplicates = (
            Attendance.objects.values('person', 'service')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        
        if not duplicates.exists():
            self.stdout.write(self.style.SUCCESS('No duplicate attendance records found.'))
            return
        
        total_deleted = 0
        
        for dup in duplicates:
            # Get all attendance records for this person/service combination
            records = Attendance.objects.filter(
                person_id=dup['person'],
                service_id=dup['service']
            ).order_by('-id')
            
            count = records.count()
            person_name = records.first().person.get_full_name() if records.first().person else 'Unknown'
            service_topic = records.first().service.topic if records.first().service else 'Unknown'
            
            self.stdout.write(
                f'Found {count} duplicate records for {person_name} in service "{service_topic}"'
            )
            
            # Keep the first (most recent) record, delete the rest
            records_to_delete = list(records[1:])
            
            for record in records_to_delete:
                if dry_run:
                    self.stdout.write(
                        f'  [DRY RUN] Would delete: ID={record.id}, State={record.state}'
                    )
                else:
                    record_id = record.id
                    record.delete()
                    self.stdout.write(
                        f'  Deleted: ID={record_id}, State={record.state}'
                    )
                total_deleted += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[DRY RUN] Would delete {total_deleted} duplicate record(s). '
                    'Run without --dry-run to actually delete them.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully deleted {total_deleted} duplicate attendance record(s).'
                )
            )
