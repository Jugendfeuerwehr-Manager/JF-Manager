from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from members.models import Member, Group, Status
from inventory.models import StorageLocation, Item, Category, Stock
from datetime import date


class Command(BaseCommand):
    help = 'Update member data and create test data for improved UI'

    def handle(self, *args, **options):
        self.stdout.write('Updating member data and creating test data...')
        
        # Create or update test members with proper dates
        group, _ = Group.objects.get_or_create(name="Jugendfeuerwehr")
        status, _ = Status.objects.get_or_create(name="Aktiv")
        
        # Update existing members with missing data
        members_updated = 0
        for member in Member.objects.all():
            if not member.joined:
                member.joined = date(2020, 1, 1)
                member.save()
                members_updated += 1
            
            if not member.birthday:
                member.birthday = date(2005, 6, 15)
                member.save()
                
            if not member.group:
                member.group = group
                member.save()
                
            if not member.status:
                member.status = status
                member.save()
        
        self.stdout.write(f'Updated {members_updated} members with missing joined dates')
        
        # Create test storage locations if they don't exist
        if not StorageLocation.objects.exists():
            hauptlager = StorageLocation.objects.create(
                name="Hauptlager",
                description="Zentrales Lager der Feuerwehr"
            )
            
            personal_bereich = StorageLocation.objects.create(
                name="Persönliche Bereiche",
                description="Persönliche Lagerplätze der Mitglieder",
                parent=hauptlager
            )
            
            # Create personal storage for first 3 members
            for i, member in enumerate(Member.objects.all()[:3]):
                personal_storage = StorageLocation.objects.create(
                    name=f"Lagerplatz {member.get_full_name()}",
                    description=f"Persönlicher Lagerplatz für {member.get_full_name()}",
                    parent=personal_bereich
                )
                member.storage_location = personal_storage
                member.save()
                
                self.stdout.write(f'Created personal storage for {member.get_full_name()}')
        
        # Create test categories and items if they don't exist
        if not Category.objects.exists():
            schutzausruestung = Category.objects.create(
                name="Schutzausrüstung",
                description="Persönliche Schutzausrüstung"
            )
            
            werkzeuge = Category.objects.create(
                name="Werkzeuge",
                description="Technische Werkzeuge und Geräte"
            )
            
            # Create test items
            Item.objects.get_or_create(
                name="Feuerwehrhelm",
                category=schutzausruestung,
                defaults={
                    'description': 'Standardhelm für Feuerwehreinsätze',
                    'is_variant_parent': False
                }
            )
            
            Item.objects.get_or_create(
                name="Atemschutzmaske",
                category=schutzausruestung,
                defaults={
                    'description': 'Vollmaske für Atemschutz',
                    'is_variant_parent': False
                }
            )
            
            Item.objects.get_or_create(
                name="Halligan Tool",
                category=werkzeuge,
                defaults={
                    'description': 'Multifunktionswerkzeug für technische Hilfeleistung',
                    'is_variant_parent': False
                }
            )
            
            self.stdout.write('Created test categories and items')
        
        # Create some test stock
        if not Stock.objects.exists():
            hauptlager = StorageLocation.objects.filter(name="Hauptlager").first()
            if hauptlager:
                for item in Item.objects.all()[:3]:
                    Stock.objects.get_or_create(
                        item=item,
                        location=hauptlager,
                        defaults={'quantity': 10}
                    )
                
                self.stdout.write('Created test stock entries')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully updated member data and created test data')
        )
