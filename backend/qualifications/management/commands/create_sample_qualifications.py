"""
Management command to create sample qualification and special task data.
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from qualifications.models.qualification import QualificationType, Qualification
from qualifications.models.special_task import SpecialTaskType, SpecialTask
from members.models import Member


class Command(BaseCommand):
    help = 'Creates sample qualification and special task data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating samples',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Qualification.objects.all().delete()
            SpecialTask.objects.all().delete()
            QualificationType.objects.all().delete()
            SpecialTaskType.objects.all().delete()

        # Create qualification types
        self.stdout.write('Creating qualification types...')
        qualification_types = [
            {
                'name': 'Jugendspange',
                'description': 'Grundausbildung für Jugendfeuerwehr',
                'expires': True,
                'validity_period': 60
            },
            {
                'name': 'Atemschutzgeräteträger',
                'description': 'Berechtigung zum Tragen von Atemschutzgeräten',
                'expires': True,
                'validity_period': 12
            },
            {
                'name': 'Maschinistenausbildung',
                'description': 'Berechtigung zum Führen von Feuerwehrfahrzeugen',
                'expires': True,
                'validity_period': 36
            },
            {
                'name': 'Erste Hilfe',
                'description': 'Erste Hilfe Grundausbildung',
                'expires': True,
                'validity_period': 24
            },
            {
                'name': 'Truppmannausbildung',
                'description': 'Grundausbildung für Feuerwehrmann/frau',
                'expires': False,
                'validity_period': None
            }
        ]

        for qual_data in qualification_types:
            qual_type, created = QualificationType.objects.get_or_create(
                name=qual_data['name'],
                defaults=qual_data
            )
            if created:
                self.stdout.write(f'Created qualification type: {qual_type.name}')

        # Create special task types
        self.stdout.write('Creating special task types...')
        special_task_types = [
            {
                'name': 'Jugendwart',
                'description': 'Leitung der Jugendfeuerwehr'
            },
            {
                'name': 'Kassenwart',
                'description': 'Verwaltung der Finanzen'
            },
            {
                'name': 'Schriftführer',
                'description': 'Protokollführung bei Sitzungen'
            },
            {
                'name': 'Gerätewart',
                'description': 'Wartung und Pflege der Ausrüstung'
            },
            {
                'name': 'Ausbilder',
                'description': 'Ausbildung neuer Mitglieder'
            }
        ]

        for task_data in special_task_types:
            task_type, created = SpecialTaskType.objects.get_or_create(
                name=task_data['name'],
                defaults=task_data
            )
            if created:
                self.stdout.write(f'Created special task type: {task_type.name}')

        # Create sample qualifications and tasks for members
        members = Member.objects.all()[:10]  # Limit to first 10 members
        
        if not members.exists():
            self.stdout.write(
                self.style.WARNING(
                    'No members found. Please create some members first.'
                )
            )
            return

        self.stdout.write(f'Creating sample data for {members.count()} members...')
        
        qual_types = QualificationType.objects.all()
        task_types = SpecialTaskType.objects.all()

        for member in members:
            # Create 1-3 random qualifications per member
            num_quals = random.randint(1, 3)
            selected_quals = random.sample(list(qual_types), min(num_quals, len(qual_types)))
            
            for qual_type in selected_quals:
                # Random issue date in the past
                days_ago = random.randint(30, 730)  # 1 month to 2 years ago
                issue_date = date.today() - timedelta(days=days_ago)
                
                # Some qualifications might be expired
                if qual_type.expires and qual_type.validity_period:
                    expiry_date = issue_date + timedelta(days=qual_type.validity_period * 30)
                else:
                    expiry_date = None

                qualification, created = Qualification.objects.get_or_create(
                    member=member,
                    type=qual_type,
                    defaults={
                        'date_acquired': issue_date,
                        'date_expires': expiry_date,
                        'issued_by': 'Kreisfeuerwehrverband',
                        'note': f'CERT-{random.randint(1000, 9999)}'
                    }
                )
                
                if created:
                    self.stdout.write(f'Created qualification: {qualification}')

            # Create 0-1 special tasks per member
            if random.choice([True, False]) and task_types.exists():
                task_type = random.choice(task_types)
                
                # Random start date
                days_ago = random.randint(30, 365)
                start_date = date.today() - timedelta(days=days_ago)
                
                # Some tasks might have end dates
                if random.choice([True, False]):
                    end_date = start_date + timedelta(days=random.randint(180, 1095))  # 6 months to 3 years
                else:
                    end_date = None

                special_task, created = SpecialTask.objects.get_or_create(
                    member=member,
                    task=task_type,
                    defaults={
                        'start_date': start_date,
                        'end_date': end_date,
                        'note': f'{task_type.description} für {member.get_full_name()}'
                    }
                )
                
                if created:
                    self.stdout.write(f'Created special task: {special_task}')

        # Show summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write(f'Qualification Types: {QualificationType.objects.count()}')
        self.stdout.write(f'Qualifications: {Qualification.objects.count()}')
        self.stdout.write(f'Special Task Types: {SpecialTaskType.objects.count()}')
        self.stdout.write(f'Special Tasks: {SpecialTask.objects.count()}')
        
        # Show some statistics
        expired_quals = Qualification.objects.filter(date_expires__lt=date.today()).count()
        expiring_soon = sum(1 for q in Qualification.objects.all() if q.expires_soon())
        active_tasks = sum(1 for t in SpecialTask.objects.all() if t.is_active)
        
        self.stdout.write('')
        self.stdout.write('Statistics:')
        self.stdout.write(f'- Expired qualifications: {expired_quals}')
        self.stdout.write(f'- Qualifications expiring soon: {expiring_soon}')
        self.stdout.write(f'- Active special tasks: {active_tasks}')
