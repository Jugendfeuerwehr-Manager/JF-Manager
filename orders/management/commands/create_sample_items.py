from django.core.management.base import BaseCommand
from orders.models import OrderableItem


class Command(BaseCommand):
    help = 'Erstellt Beispiel-Ausrüstungsgegenstände für die Bestellungen'

    def handle(self, *args, **options):
        # Helme (Einheitsgröße)
        helmet, created = OrderableItem.objects.get_or_create(
            name='Helm',
            category='Schutzausrüstung',
            defaults={
                'description': 'Feuerwehrhelm nach DIN EN 443',
                'has_sizes': False,
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Erstellt: {helmet}'))

        # Hosen (Kindergrößen und Erwachsenengrößen)
        trousers, created = OrderableItem.objects.get_or_create(
            name='Überhose',
            category='Schutzkleidung',
            defaults={
                'description': 'Feuerwehr-Überhose nach HuPF Teil 3',
                'has_sizes': True,
                'available_sizes': '98,104,110,116,122,128,134,140,146,152,S,M,L,XL,XXL,XXXL',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Erstellt: {trousers}'))

        # Jacken
        jacket, created = OrderableItem.objects.get_or_create(
            name='Überjacke',
            category='Schutzkleidung',
            defaults={
                'description': 'Feuerwehr-Überjacke nach HuPF Teil 3',
                'has_sizes': True,
                'available_sizes': '98,104,110,116,122,128,134,140,146,152,S,M,L,XL,XXL,XXXL',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Erstellt: {jacket}'))

        # Stiefel
        boots, created = OrderableItem.objects.get_or_create(
            name='Stiefel',
            category='Schutzausrüstung',
            defaults={
                'description': 'Feuerwehrstiefel nach DIN EN 15090',
                'has_sizes': True,
                'available_sizes': '27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Erstellt: {boots}'))

        # Handschuhe
        gloves, created = OrderableItem.objects.get_or_create(
            name='Handschuhe',
            category='Schutzausrüstung',
            defaults={
                'description': 'Technische Handschuhe nach DIN EN 659',
                'has_sizes': True,
                'available_sizes': 'XS,S,M,L,XL,XXL',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Erstellt: {gloves}'))

        # T-Shirts
        tshirt, created = OrderableItem.objects.get_or_create(
            name='T-Shirt',
            category='Dienstkleidung',
            defaults={
                'description': 'Feuerwehr T-Shirt mit Vereinslogo',
                'has_sizes': True,
                'available_sizes': '98,104,110,116,122,128,134,140,146,152,XS,S,M,L,XL,XXL,XXXL',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Erstellt: {tshirt}'))

        self.stdout.write(
            self.style.SUCCESS(
                'Beispiel-Ausrüstungsgegenstände wurden erfolgreich erstellt!'
            )
        )
