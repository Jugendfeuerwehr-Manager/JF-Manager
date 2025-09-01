from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from inventory.models import Category, Item, StorageLocation, Transaction
from members.models.member import Member

User = get_user_model()


class Command(BaseCommand):
    help = 'Erstellt Beispieldaten für das Inventarsystem'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Lösche alle bestehenden Inventardaten vor dem Erstellen',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Lösche bestehende Inventardaten...')
            Transaction.objects.all().delete()
            Item.objects.filter(name__isnull=False).exclude(name='').delete()
            StorageLocation.objects.all().delete()
            Category.objects.filter(name__in=[
                'Uniformen', 'Ausrüstung', 'Fahrzeuge', 'Werkzeug', 'Erste Hilfe'
            ]).delete()

        # Kategorien erstellen
        self.stdout.write('Erstelle Kategorien...')
        categories = {
            'Uniformen': {
                "größe": "string",
                "farbe": "string",
                "material": "string"
            },
            'Ausrüstung': {
                "typ": "string",
                "material": "string",
                "gewicht": "number"
            },
            'Fahrzeuge': {
                "kennzeichen": "string",
                "baujahr": "number",
                "hersteller": "string"
            },
            'Werkzeug': {
                "typ": "string",
                "zustand": "string"
            },
            'Erste Hilfe': {
                "ablaufdatum": "date",
                "hersteller": "string"
            }
        }

        category_objects = {}
        for cat_name, schema in categories.items():
            cat, created = Category.objects.get_or_create(
                name=cat_name,
                defaults={'schema': schema}
            )
            category_objects[cat_name] = cat
            if created:
                self.stdout.write(f'  ✓ {cat_name}')

        # Lagerorte erstellen
        self.stdout.write('Erstelle Lagerorte...')
        locations = [
            'Hauptlager',
            'Fahrzeughalle',
            'Jugendschrank',
            'Erste-Hilfe-Raum',
            'Werkstatt'
        ]

        location_objects = {}
        for loc_name in locations:
            loc, created = StorageLocation.objects.get_or_create(
                name=loc_name,
                defaults={'is_member': False}
            )
            location_objects[loc_name] = loc
            if created:
                self.stdout.write(f'  ✓ {loc_name}')

        # Mitglieder-Lagerorte erstellen (falls Mitglieder vorhanden)
        members = Member.objects.all()[:3]  # Erste 3 Mitglieder
        for member in members:
            loc, created = StorageLocation.objects.get_or_create(
                name=f'{member.name} {member.lastname}',
                defaults={
                    'is_member': True,
                    'member': member
                }
            )
            if created:
                self.stdout.write(f'  ✓ Mitglied: {member.name} {member.lastname}')

        # Artikel erstellen
        self.stdout.write('Erstelle Artikel...')
        articles = [
            {
                'name': 'Uniform Jacke',
                'category': 'Uniformen',
                'base_unit': 'Stück',
                'attributes': {'größe': 'L', 'farbe': 'dunkelblau', 'material': 'Baumwolle'}
            },
            {
                'name': 'Feuerwehrhelm',
                'category': 'Ausrüstung',
                'base_unit': 'Stück',
                'attributes': {'typ': 'Schutzhelm', 'material': 'Kunststoff', 'gewicht': 0.8}
            },
            {
                'name': 'Löschschlauch',
                'category': 'Ausrüstung',
                'base_unit': 'Meter',
                'attributes': {'typ': 'C-Schlauch', 'material': 'Textil'}
            },
            {
                'name': 'Verbandsmaterial',
                'category': 'Erste Hilfe',
                'base_unit': 'Packung',
                'attributes': {'ablaufdatum': '2025-12-31', 'hersteller': 'MediCorp'}
            },
            {
                'name': 'Atemschutzgerät',
                'category': 'Ausrüstung',
                'base_unit': 'Stück',
                'attributes': {'typ': 'Pressluftatmer', 'gewicht': 15.5}
            },
            {
                'name': 'Strahlrohr',
                'category': 'Ausrüstung',
                'base_unit': 'Stück',
                'attributes': {'typ': 'Mehrzweckstrahlrohr', 'material': 'Aluminium'}
            }
        ]

        item_objects = []
        for article in articles:
            item, created = Item.objects.get_or_create(
                name=article['name'],
                defaults={
                    'category': category_objects[article['category']],
                    'base_unit': article['base_unit'],
                    'attributes': article['attributes']
                }
            )
            item_objects.append(item)
            if created:
                self.stdout.write(f'  ✓ {article["name"]}')

        # Beispiel-Transaktionen erstellen
        self.stdout.write('Erstelle Beispiel-Transaktionen...')
        
        # Admin-User für Transaktionen
        admin_user = User.objects.filter(is_superuser=True).first()
        
        example_transactions = [
            {
                'type': 'IN',
                'item': item_objects[0],  # Uniform Jacke
                'target': location_objects['Hauptlager'],
                'quantity': 10,
                'note': 'Neue Lieferung Uniformjacken'
            },
            {
                'type': 'IN',
                'item': item_objects[1],  # Feuerwehrhelm
                'target': location_objects['Hauptlager'],
                'quantity': 15,
                'note': 'Neue Helme eingetroffen'
            },
            {
                'type': 'MOVE',
                'item': item_objects[0],  # Uniform Jacke
                'source': location_objects['Hauptlager'],
                'target': location_objects['Jugendschrank'],
                'quantity': 3,
                'note': 'Für Jugendarbeit bereitgestellt'
            }
        ]

        for trans_data in example_transactions:
            transaction = Transaction.objects.create(
                transaction_type=trans_data['type'],
                item=trans_data['item'],
                source=trans_data.get('source'),
                target=trans_data.get('target'),
                quantity=trans_data['quantity'],
                note=trans_data['note'],
                user=admin_user
            )
            self.stdout.write(f'  ✓ {trans_data["type"]}: {trans_data["item"].name}')

        self.stdout.write(
            self.style.SUCCESS('Beispieldaten erfolgreich erstellt!')
        )
        self.stdout.write(
            'Sie können nun das Inventarsystem unter /inventory/ aufrufen.'
        )
