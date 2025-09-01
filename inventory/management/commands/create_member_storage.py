from django.core.management.base import BaseCommand
from django.db import transaction
from members.models import Member
from inventory.models import StorageLocation


class Command(BaseCommand):
    help = 'Erstellt automatisch Lagerplätze für alle Mitglieder, die noch keinen haben'

    def add_arguments(self, parser):
        parser.add_argument(
            '--parent',
            type=int,
            help='ID des übergeordneten Lagerorts für alle Mitglieder-Lagerplätze',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Zeigt nur an, was erstellt würde, ohne Änderungen vorzunehmen',
        )

    def handle(self, *args, **options):
        parent_id = options.get('parent')
        dry_run = options.get('dry_run', False)
        
        parent_location = None
        if parent_id:
            try:
                parent_location = StorageLocation.objects.get(pk=parent_id)
                self.stdout.write(
                    self.style.SUCCESS(f'Übergeordneter Lagerort: {parent_location.name}')
                )
            except StorageLocation.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Lagerort mit ID {parent_id} nicht gefunden')
                )
                return

        # Finde Mitglieder ohne Lagerplatz
        members_without_storage = Member.objects.filter(
            personal_storage_location__isnull=True
        ).order_by('lastname', 'name')

        if not members_without_storage.exists():
            self.stdout.write(
                self.style.SUCCESS('Alle Mitglieder haben bereits einen Lagerplatz.')
            )
            return

        self.stdout.write(
            f'Gefunden: {members_without_storage.count()} Mitglieder ohne Lagerplatz'
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('\n--- DRY RUN MODE ---'))
            for member in members_without_storage:
                storage_name = f"Lagerplatz {member.name} {member.lastname}"
                self.stdout.write(f'Würde erstellen: {storage_name}')
            return

        created_count = 0
        with transaction.atomic():
            for member in members_without_storage:
                storage_name = f"Lagerplatz {member.name} {member.lastname}"
                
                try:
                    storage_location = StorageLocation.objects.create(
                        name=storage_name,
                        parent=parent_location,
                        is_member=True,
                        member=member
                    )
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Erstellt: {storage_location.name}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Fehler bei {storage_name}: {str(e)}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'\n{created_count} Lagerplätze erfolgreich erstellt.')
        )
