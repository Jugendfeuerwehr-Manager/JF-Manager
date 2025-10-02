from django.core.management.base import BaseCommand
from inventory.models import Category, Item, ItemVariant, StorageLocation, Stock


class Command(BaseCommand):
    help = 'Erstellt Test-Daten für das Varianten-System'

    def handle(self, *args, **options):
        self.stdout.write('Erstelle Test-Daten für Varianten...')
        
        # Erstelle Kategorien mit Schema
        self.stdout.write('Erstelle Kategorien...')
        
        clothing_category, created = Category.objects.get_or_create(
            name='Kleidung',
            defaults={
                'schema': {
                    'größe': 'string',
                    'farbe': 'string',
                    'material': 'string'
                }
            }
        )
        if created:
            self.stdout.write(f'  ✓ Kategorie "{clothing_category.name}" erstellt')
        
        equipment_category, created = Category.objects.get_or_create(
            name='Ausrüstung',
            defaults={
                'schema': {
                    'größe': 'string',
                    'gewicht': 'number',
                    'typ': 'string'
                }
            }
        )
        if created:
            self.stdout.write(f'  ✓ Kategorie "{equipment_category.name}" erstellt')
        
        # Erstelle Lagerorte falls nicht vorhanden
        self.stdout.write('Erstelle Lagerorte...')
        
        main_storage, created = StorageLocation.objects.get_or_create(
            name='Hauptlager',
            defaults={'is_member': False}
        )
        if created:
            self.stdout.write(f'  ✓ Lagerort "{main_storage.name}" erstellt')
        
        clothing_storage, created = StorageLocation.objects.get_or_create(
            name='Kleiderkammer',
            defaults={'parent': main_storage, 'is_member': False}
        )
        if created:
            self.stdout.write(f'  ✓ Lagerort "{clothing_storage.name}" erstellt')
        
        # Erstelle Artikel mit Varianten
        self.stdout.write('Erstelle Artikel mit Varianten...')
        
        # Feuerwehrhose
        pants_item, created = Item.objects.get_or_create(
            name='Feuerwehrhose',
            defaults={
                'category': clothing_category,
                'base_unit': 'Stück',
                'is_variant_parent': True,
                'attributes': {
                    'material': 'Nomex',
                    'farbe': 'schwarz'
                }
            }
        )
        if created:
            self.stdout.write(f'  ✓ Artikel "{pants_item.name}" erstellt')
        
        # Varianten für Feuerwehrhose
        pants_sizes = ['164', '176', '188', '200']
        for size in pants_sizes:
            variant, created = ItemVariant.objects.get_or_create(
                parent_item=pants_item,
                variant_attributes={'größe': size},
                defaults={
                    'sku': f'FW-HOSE-{size}'
                }
            )
            if created:
                self.stdout.write(f'    ✓ Variante "Größe {size}" erstellt')
                
                # Erstelle Bestand für Variante
                stock, stock_created = Stock.objects.get_or_create(
                    item_variant=variant,
                    location=clothing_storage,
                    defaults={'quantity': 5}  # 5 Hosen jeder Größe
                )
                if stock_created:
                    self.stdout.write(f'      ✓ Bestand von {stock.quantity} Stück angelegt')
        
        # Feuerwehrjacke
        jacket_item, created = Item.objects.get_or_create(
            name='Feuerwehrjacke',
            defaults={
                'category': clothing_category,
                'base_unit': 'Stück',
                'is_variant_parent': True,
                'attributes': {
                    'material': 'Nomex',
                    'farbe': 'schwarz'
                }
            }
        )
        if created:
            self.stdout.write(f'  ✓ Artikel "{jacket_item.name}" erstellt')
        
        # Varianten für Feuerwehrjacke
        jacket_sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
        for size in jacket_sizes:
            variant, created = ItemVariant.objects.get_or_create(
                parent_item=jacket_item,
                variant_attributes={'größe': size},
                defaults={
                    'sku': f'FW-JACKE-{size}'
                }
            )
            if created:
                self.stdout.write(f'    ✓ Variante "Größe {size}" erstellt')
                
                # Erstelle Bestand für Variante
                stock, stock_created = Stock.objects.get_or_create(
                    item_variant=variant,
                    location=clothing_storage,
                    defaults={'quantity': 3}  # 3 Jacken jeder Größe
                )
                if stock_created:
                    self.stdout.write(f'      ✓ Bestand von {stock.quantity} Stück angelegt')
        
        # Atemschutzmaske mit verschiedenen Größen
        mask_item, created = Item.objects.get_or_create(
            name='Atemschutzmaske',
            defaults={
                'category': equipment_category,
                'base_unit': 'Stück',
                'is_variant_parent': True,
                'attributes': {
                    'typ': 'Vollmaske'
                }
            }
        )
        if created:
            self.stdout.write(f'  ✓ Artikel "{mask_item.name}" erstellt')
        
        # Varianten für Atemschutzmaske
        mask_sizes = ['S', 'M', 'L']
        for size in mask_sizes:
            variant, created = ItemVariant.objects.get_or_create(
                parent_item=mask_item,
                variant_attributes={'größe': size},
                defaults={
                    'sku': f'AS-MASKE-{size}'
                }
            )
            if created:
                self.stdout.write(f'    ✓ Variante "Größe {size}" erstellt')
                
                # Erstelle Bestand für Variante
                stock, stock_created = Stock.objects.get_or_create(
                    item_variant=variant,
                    location=main_storage,
                    defaults={'quantity': 8}  # 8 Masken jeder Größe
                )
                if stock_created:
                    self.stdout.write(f'      ✓ Bestand von {stock.quantity} Stück angelegt')
        
        # Erstelle auch einige Artikel ohne Varianten
        normal_item, created = Item.objects.get_or_create(
            name='Feuerlöscher 6L',
            defaults={
                'category': equipment_category,
                'base_unit': 'Stück',
                'is_variant_parent': False,
                'attributes': {
                    'typ': 'Schaum',
                    'gewicht': 6
                }
            }
        )
        if created:
            self.stdout.write(f'  ✓ Normaler Artikel "{normal_item.name}" erstellt')
            
            # Bestand für normalen Artikel
            stock, stock_created = Stock.objects.get_or_create(
                item=normal_item,
                location=main_storage,
                defaults={'quantity': 12}
            )
            if stock_created:
                self.stdout.write(f'    ✓ Bestand von {stock.quantity} Stück angelegt')
        
        self.stdout.write(self.style.SUCCESS('Test-Daten erfolgreich erstellt!'))
        
        # Zusammenfassung ausgeben
        total_items = Item.objects.count()
        total_variants = ItemVariant.objects.count()
        total_stock_entries = Stock.objects.count()
        
        self.stdout.write('\nZusammenfassung:')
        self.stdout.write(f'  - {total_items} Artikel')
        self.stdout.write(f'  - {total_variants} Varianten')
        self.stdout.write(f'  - {total_stock_entries} Bestandseinträge')
        self.stdout.write('\nDie Test-Daten können nun in der Anwendung verwendet werden!')
