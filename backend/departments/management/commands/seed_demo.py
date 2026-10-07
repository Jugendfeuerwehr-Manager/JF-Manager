"""Fill an EMPTY database with fictitious, reproducible demo data for all modules.

Usage: python manage.py seed_demo [--password PW] [--allow-non-debug]
All names, addresses and e-mail addresses are invented (domain example.invalid).
Nothing is sent: no e-mail, no push (push stays unconfigured).
"""

import random
import secrets
from datetime import datetime, time, timedelta
from io import StringIO
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

DEMO_DOMAIN = "demo.example.invalid"

FIRST_NAMES = [
    ("Lena", "female"),
    ("Finn", "male"),
    ("Mila", "female"),
    ("Noah", "male"),
    ("Emilia", "female"),
    ("Ben", "male"),
    ("Luca", "male"),
    ("Lea", "female"),
    ("Jonas", "male"),
    ("Anna", "female"),
    ("Elias", "male"),
    ("Nele", "female"),
    ("Paul", "male"),
    ("Clara", "female"),
    ("Leon", "male"),
    ("Ida", "female"),
    ("Theo", "male"),
    ("Marie", "female"),
    ("Emil", "male"),
    ("Lina", "female"),
    ("Anton", "male"),
    ("Frieda", "female"),
    ("Jakob", "male"),
    ("Hanna", "female"),
    ("Mats", "male"),
    ("Greta", "female"),
    ("Karl", "male"),
    ("Romy", "female"),
    ("Oskar", "male"),
    ("Kim", "diverse"),
]
LAST_NAMES = [
    "Berg",
    "Weber",
    "Hoffmann",
    "Fischer",
    "Koch",
    "Schneider",
    "Hartmann",
    "Wagner",
    "Becker",
    "Klein",
    "Wolf",
    "Braun",
    "Zimmermann",
    "Krüger",
    "Lange",
    "Schmitt",
    "Neumann",
    "Schwarz",
    "Vogel",
    "Frank",
    "Roth",
    "Busch",
    "Lorenz",
    "Kühn",
    "Haas",
    "Sauer",
    "Arnold",
    "Brandt",
    "Engel",
    "Pohl",
]
STREETS = ["Lindenweg", "Am Feuerwehrhaus", "Brunnenstraße", "Eichenallee", "Wiesengrund", "Mühlweg", "Kirchplatz"]

# (key, first, last, superuser, [(role_key, department_code or None)])
ACCOUNTS = [
    ("admin", "Alex", "Sommer", True, []),
    ("jugendwart", "Jana", "Krüger", False, [("youth_director", None)]),
    ("leitung.mitte", "Tobias", "Lehmann", False, [("department_youth_director", "mitte")]),
    ("leitung.nord", "Sabine", "Hahn", False, [("department_youth_director", "nord")]),
    ("leitung.kinder", "Miriam", "Graf", False, [("department_youth_director", "kinder")]),
    ("betreuer.mitte", "Jan", "Keller", False, [("youth_leader", "mitte")]),
    ("betreuer.nord", "Sam", "Winter", False, [("supervisor", "nord")]),
    (
        "ausbilder",
        "Mira",
        "Brandt",
        False,
        [("training_planner", "mitte"), ("training_planner", "nord"), ("library_editor", None)],
    ),
    (
        "geraetewart",
        "Uwe",
        "Seidel",
        False,
        [("inventory_manager_organization", None), ("order_manager_organization", None)],
    ),
    ("kommunikation", "Petra", "Albrecht", False, [("email_communicator_organization", None)]),
]

DEPARTMENTS = [
    ("mitte", "Jugendfeuerwehr Musterstadt-Mitte", "#b91c1c", ["Gruppe 1", "Gruppe 2", "Leistungsgruppe"], 24),
    ("nord", "Jugendfeuerwehr Musterstadt-Nord", "#1d4ed8", ["Gruppe Nord", "Neueinsteiger"], 16),
    ("kinder", "Kinderfeuerwehr Löschzwerge", "#ca8a04", ["Löschzwerge"], 12),
]


class Command(BaseCommand):
    help = "Legt vollständige fiktive Demodaten in einer LEEREN Datenbank an (Entwicklung, Vorführung)."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Gemeinsames Passwort aller Demokonten (Standard: zufällig).")
        parser.add_argument(
            "--allow-non-debug",
            action="store_true",
            help="Auch ohne DEBUG ausführen (nur für eigene Vorführsysteme ohne echte Daten).",
        )
        parser.add_argument("--seed", type=int, default=112, help="Startwert für reproduzierbare Daten.")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["allow_non_debug"]:
            raise CommandError("seed_demo läuft nur mit DEBUG=True oder ausdrücklich mit --allow-non-debug.")
        from members.models import Member

        users = get_user_model().objects.exclude(username="AnonymousUser")
        if Member.objects.exists() or users.exists():
            raise CommandError("Datenbestand ist nicht leer. Demodaten nur in eine frische Datenbank laden.")
        self.rng = random.Random(options["seed"])
        self.today = timezone.localdate()
        password = options["password"] or secrets.token_urlsafe(12)
        # Seeding never sends anything, whatever SMTP configuration exists.
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"), transaction.atomic():
            self.seed(password)
        self.report(password)

    # ------------------------------------------------------------------ helpers
    def aware(self, day, at):
        return timezone.make_aware(datetime.combine(day, at))

    def phone(self):
        return f"+49 151 {self.rng.randint(1000000, 9999999)}"

    def address(self):
        return {
            "street": f"{self.rng.choice(STREETS)} {self.rng.randint(1, 60)}",
            "zip_code": "12345",
            "city": "Musterstadt",
        }

    # ------------------------------------------------------------------ seed
    def seed(self, password):
        self.seed_organisation()
        self.seed_accounts(password)
        self.seed_members()
        self.seed_qualifications()
        self.seed_inventory()
        self.seed_orders()
        self.seed_training()
        self.seed_services()
        self.seed_communication()

    def seed_organisation(self):
        from departments.models import Department
        from members.models import EventType, Group, Status

        self.departments, self.groups = {}, {}
        for code, name, color, groups, _ in DEPARTMENTS:
            department = Department.objects.create(
                name=name,
                code=code,
                color=color,
                address="Am Feuerwehrhaus 1, 12345 Musterstadt",
                description="Fiktive Abteilung für Demonstrationen.",
            )
            self.departments[code] = department
            self.groups[code] = [Group.objects.create(name=group, department=department) for group in groups]
            for event in ("Jugendflamme abgelegt", "Leistungsspange abgelegt", "Zeltlager teilgenommen"):
                EventType.objects.create(name=event, department=department)
        self.statuses = {
            name: Status.objects.create(name=name, color=color)
            for name, color in (
                ("Aktiv", "#16a34a"),
                ("Anwärter", "#0ea5e9"),
                ("Passiv", "#64748b"),
                ("Übertritt Einsatzabteilung", "#9333ea"),
            )
        }

    def seed_accounts(self, password):
        from departments.assignment_sources import set_local_groups
        from departments.models import RoleTemplate, UserDepartmentRole
        from users.mfa import generate_secret
        from users.mfa_policy import mfa_required
        from users.models import MFADevice

        model = get_user_model()
        self.accounts = {}
        for username, first, last, superuser, roles in ACCOUNTS:
            values = dict(
                username=username,
                first_name=first,
                last_name=last,
                email=f"{username}@{DEMO_DOMAIN}",
                mobile_phone=self.phone(),
                **self.address(),
            )
            user = (model.objects.create_superuser if superuser else model.objects.create_user)(
                password=password, **values
            )
            codes = {code for _, code in roles if code} or (set(self.departments) if not roles or superuser else set())
            # Mitte has the richest data; it is the start view for every account that can see it.
            start = "mitte" if "mitte" in codes or not codes else sorted(codes)[0]
            user.favorite_department = self.departments[start]
            user.save(update_fields=["favorite_department"])
            for code in codes:
                UserDepartmentRole.objects.get_or_create(user=user, department=self.departments[code])
            by_scope = {}
            for key, code in roles:
                by_scope.setdefault(code, []).append(RoleTemplate.objects.get(key=key).group)
            for code, groups in by_scope.items():
                set_local_groups(user, self.departments[code].pk if code else None, groups)
            self.accounts[username] = user
        # Privileged demo accounts get a confirmed authenticator, readable via `manage.py demo_totp`.
        self.totp_accounts = []
        for user in self.accounts.values():
            user = model.objects.get(pk=user.pk)
            if mfa_required(user):
                MFADevice.objects.create(user=user, secret=generate_secret(), confirmed_at=timezone.now())
                self.totp_accounts.append(user.username)
        self.instructors = [self.accounts[name] for name in ("ausbilder", "betreuer.mitte", "leitung.mitte")]

    def seed_members(self):
        from members.models import Event, EventType, Member, Parent

        self.members = {code: [] for code in self.departments}
        names = iter(self.rng.sample([(f, g, last) for f, g in FIRST_NAMES for last in LAST_NAMES], 200))
        for code, _, _, _, count in DEPARTMENTS:
            department = self.departments[code]
            for index in range(count):
                first, gender, last = next(names)
                age = self.rng.randint(6, 9) if code == "kinder" else self.rng.randint(10, 17)
                birthday = self.today.replace(year=self.today.year - age) - timedelta(days=self.rng.randint(0, 360))
                status = (
                    self.statuses["Anwärter"]
                    if index % 9 == 0
                    else self.statuses["Passiv"]
                    if index % 13 == 0
                    else self.statuses["Übertritt Einsatzabteilung"]
                    if age >= 17
                    else self.statuses["Aktiv"]
                )
                member = Member.objects.create(
                    name=first,
                    lastname=last,
                    gender=gender,
                    birthday=birthday,
                    joined=self.today - timedelta(days=self.rng.randint(30, 6 * 365)),
                    group=self.groups[code][index % len(self.groups[code])],
                    status=status,
                    email=f"{first.lower()}.{last.lower()}@{DEMO_DOMAIN}".replace("ü", "ue").replace("ö", "oe"),
                    mobile=self.phone() if age >= 12 else "",
                    canSwimm=self.rng.random() > 0.15,
                    identityCardNumber=f"JF-{code.upper()}-{index + 1:03d}",
                    notes="Allergie: Wespenstich – Notfallset im Erste-Hilfe-Rucksack." if index == 3 else "",
                    **self.address(),
                )
                member.departments.add(department)
                parent = Parent.objects.create(
                    name=self.rng.choice(["Kerstin", "Michael", "Sandra", "Thomas", "Julia", "Andreas"]),
                    lastname=last,
                    email=f"eltern.{last.lower()}{index}@{DEMO_DOMAIN}".replace("ü", "ue").replace("ö", "oe"),
                    mobile=self.phone(),
                    **self.address(),
                )
                parent.children.add(member)
                self.members[code].append(member)
            for member in self.members[code][:6]:
                Event.objects.create(
                    type=EventType.objects.filter(department=department).first(),
                    member=member,
                    datetime=self.today - timedelta(days=self.rng.randint(20, 400)),
                    notes="Mit Bravour bestanden.",
                )

    def seed_qualifications(self):
        from qualifications.models import Qualification, QualificationType, SpecialTask, SpecialTaskType

        def qtype(name, months=None, text=""):
            return QualificationType.objects.create(
                name=name, expires=months is not None, validity_period=months, description=text
            )

        first_aid = qtype("Erste-Hilfe-Ausbildung", 24, "Pflicht für alle Betreuenden.")
        juleica = qtype("Jugendleiter-Card (Juleica)", 36, "Jugendleiterausbildung.")
        driver = qtype("Fahrberechtigung Mannschaftstransportfahrzeug", 12)
        basic = qtype("Truppmann Teil 1")
        flame = [qtype(f"Jugendflamme Stufe {n}") for n in (1, 2, 3)]
        spange = qtype("Leistungsspange")
        swim = qtype("Schwimmabzeichen Bronze")
        # Expiry spread over the 30/60/90-day windows plus expired and long-valid records.
        offsets = [-20, 12, 25, 45, 75, 140, 400, 600]
        for index, user in enumerate(self.accounts.values()):
            for kind, months in ((first_aid, 24), (juleica, 36)):
                expires = self.today + timedelta(days=offsets[(index + months) % len(offsets)])
                Qualification.objects.create(
                    type=kind,
                    user=user,
                    date_acquired=expires - timedelta(days=30 * months),
                    date_expires=expires,
                    issued_by="Kreisfeuerwehrverband Musterkreis",
                )
            if index % 2 == 0:
                Qualification.objects.create(type=basic, user=user, date_acquired=self.today - timedelta(days=2000))
        for user in (self.accounts["geraetewart"], self.accounts["leitung.mitte"]):
            Qualification.objects.create(
                type=driver,
                user=user,
                date_acquired=self.today - timedelta(days=330),
                date_expires=self.today + timedelta(days=35),
            )
        for members in self.members.values():
            for index, member in enumerate(members):
                age = (self.today - member.birthday).days // 365
                for level in range(min(3, max(0, age - 9))):
                    Qualification.objects.create(
                        type=flame[level], member=member, date_acquired=self.today - timedelta(days=365 * (3 - level))
                    )
                if age >= 15 and index % 2 == 0:
                    Qualification.objects.create(
                        type=spange, member=member, date_acquired=self.today - timedelta(days=200)
                    )
                if member.canSwimm:
                    Qualification.objects.create(
                        type=swim, member=member, date_acquired=self.today - timedelta(days=700)
                    )
                # Youth first-aid courses expire too; spread them over the dashboard's 30/60/90-day windows.
                if age >= 13 and index % 3 == 0:
                    expires = self.today + timedelta(days=offsets[index % len(offsets)])
                    Qualification.objects.create(
                        type=first_aid,
                        member=member,
                        date_expires=expires,
                        date_acquired=expires - timedelta(days=730),
                        issued_by="Jugendrotkreuz Musterstadt",
                    )
        tasks = {
            name: SpecialTaskType.objects.create(name=name, description=text)
            for name, text in (
                ("Kassenwart", "Führt die Jugendkasse."),
                ("Jugendsprecher", "Vertritt die Jugendlichen."),
                ("Atemschutz-Gerätewart", "Pflegt Geräte und Prüffristen."),
            )
        }
        SpecialTask.objects.create(
            task=tasks["Kassenwart"], user=self.accounts["betreuer.mitte"], start_date=self.today - timedelta(days=500)
        )
        for code in ("mitte", "nord"):
            SpecialTask.objects.create(
                task=tasks["Jugendsprecher"], member=self.members[code][1], start_date=self.today - timedelta(days=120)
            )
        SpecialTask.objects.create(
            task=tasks["Atemschutz-Gerätewart"],
            user=self.accounts["geraetewart"],
            start_date=self.today - timedelta(days=900),
            end_date=self.today - timedelta(days=30),
            note="Abgegeben an Kreis.",
        )

    def seed_inventory(self):
        from inventory.models import Category, Item, ItemVariant, StorageLocation, Transaction
        from inventory.opening_stock import book_opening_stock
        from orders.services.inventory_sync import sync_orderable_item

        clerk = self.accounts["geraetewart"]
        clothing = Category.objects.create(name="Bekleidung", schema={"größe": "string", "farbe": "string"})
        equipment = Category.objects.create(name="Ausrüstung", schema={"typ": "string", "material": "string"})
        first_aid = Category.objects.create(name="Erste Hilfe", schema={"ablaufdatum": "date"})
        training = Category.objects.create(name="Übungsmaterial", schema={"zustand": "string"})
        central = StorageLocation.objects.create(name="Kreislager")
        self.locations = {}
        for code, department in self.departments.items():
            base = StorageLocation.objects.create(
                name=f"Gerätehaus {department.name.split()[-1]}", department=department
            )
            self.locations[code] = {
                "base": base,
                "kleiderkammer": StorageLocation.objects.create(
                    name="Kleiderkammer", parent=base, department=department
                ),
                "uebung": StorageLocation.objects.create(name="Übungsschrank", parent=base, department=department),
            }

        def variants(item, sizes, location, quantity):
            created = [
                ItemVariant.objects.create(
                    parent_item=item, variant_attributes={"größe": size}, sku=f"{item.pk:03d}-{size}"
                )
                for size in sizes
            ]
            for index, variant in enumerate(created):
                book_opening_stock(location, quantity + index % 3, item_variant=variant, user=clerk)
            sync_orderable_item(item)
            return created

        self.items = {}
        for code in self.departments:
            spot = self.locations[code]
            department = self.departments[code]
            kids = code == "kinder"
            sizes = ["116", "128", "140", "152"] if kids else ["140", "152", "164", "176", "S", "M", "L"]
            shirt = Item.objects.create(
                name="T-Shirt Jugendfeuerwehr",
                category=clothing,
                base_unit="Stück",
                is_variant_parent=True,
                department=department,
                attributes={"farbe": "dunkelblau"},
            )
            jacket = Item.objects.create(
                name="Schutzjacke Jugend",
                category=clothing,
                base_unit="Stück",
                is_variant_parent=True,
                department=department,
                attributes={"farbe": "orange"},
            )
            helmet = Item.objects.create(
                name="Jugendfeuerwehrhelm",
                category=equipment,
                base_unit="Stück",
                department=department,
                attributes={"typ": "Schutzhelm", "material": "PA"},
            )
            gloves = Item.objects.create(
                name="Handschuhe", category=equipment, base_unit="Paar", is_variant_parent=True, department=department
            )
            hose = Item.objects.create(
                name="C-Schlauch 15 m",
                category=training,
                base_unit="Stück",
                department=department,
                attributes={"zustand": "gut"},
            )
            cones = Item.objects.create(name="Leitkegel", category=training, base_unit="Stück", department=department)
            kit = Item.objects.create(
                name="Erste-Hilfe-Rucksack",
                category=first_aid,
                base_unit="Stück",
                department=department,
                attributes={"ablaufdatum": str(self.today + timedelta(days=50))},
            )
            shirts = variants(shirt, sizes, spot["kleiderkammer"], 6)
            variants(jacket, sizes[1:], spot["kleiderkammer"], 2)
            variants(gloves, ["6", "7", "8", "9"], spot["kleiderkammer"], 4)
            for item, quantity, location in (
                (helmet, 8, spot["kleiderkammer"]),
                (hose, 6, spot["uebung"]),
                (cones, 20, spot["uebung"]),
                (kit, 2, spot["base"]),
            ):
                book_opening_stock(location, quantity, item=item, user=clerk)
                sync_orderable_item(item)
            self.items[code] = {"shirt": shirt, "helmet": helmet, "hose": hose, "cones": cones, "kit": kit}
            # Loans to members create their personal storage locations, like an issue at the counter.
            for member in self.members[code][:5]:
                target, _ = StorageLocation.objects.get_or_create(
                    member=member,
                    defaults={"name": f"{member.name} {member.lastname}", "is_member": True, "department": department},
                )
                Transaction.objects.create(
                    transaction_type="LOAN",
                    source=spot["kleiderkammer"],
                    target=target,
                    item=helmet,
                    quantity=1,
                    user=clerk,
                    note="Ausgabe bei Eintritt",
                )
                Transaction.objects.create(
                    transaction_type="LOAN",
                    source=spot["kleiderkammer"],
                    target=target,
                    item_variant=shirts[1],
                    quantity=1,
                    user=clerk,
                    note="Ausgabe bei Eintritt",
                )
            Transaction.objects.create(
                transaction_type="DISCARD",
                discard_reason="DAMAGED",
                source=spot["uebung"],
                item=hose,
                quantity=1,
                user=clerk,
                note="Schlauch geplatzt bei Übung",
            )
            Transaction.objects.create(
                transaction_type="MOVE",
                source=spot["uebung"],
                target=spot["base"],
                item=cones,
                quantity=4,
                user=clerk,
                note="Für Verkehrsabsicherung",
            )
        reserve = Item.objects.create(name="Rettungsdecke", category=first_aid, base_unit="Stück")
        book_opening_stock(central, 50, item=reserve, user=clerk)
        sync_orderable_item(reserve)

    def seed_orders(self):
        import inventory.api  # noqa: F401  (load first: orders and inventory serializers import each other)
        from orders.api.serializers.order_item import OrderItemUpdateSerializer
        from orders.models import Order, OrderableItem, OrderItem, OrderStatus

        call_command("create_default_email_templates", stdout=StringIO())
        status = {s.code: s for s in OrderStatus.objects.all()}
        request = SimpleNamespace(user=self.accounts["admin"])

        def move(item, code, **extra):
            serializer = OrderItemUpdateSerializer(
                item, data={"status": status[code].pk, **extra}, partial=True, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            return serializer.save()

        for code in ("mitte", "nord"):
            shirt = OrderableItem.objects.get(inventory_item=self.items[code]["shirt"])
            helmet = OrderableItem.objects.get(inventory_item=self.items[code]["helmet"])
            store = self.locations[code]["kleiderkammer"]
            for index, member in enumerate(self.members[code][5:13]):
                order = Order.objects.create(
                    member=member,
                    ordered_by=self.accounts["geraetewart"],
                    department=self.departments[code],
                    notes="Neueinkleidung" if index % 2 == 0 else "Ersatz",
                )
                size = shirt.available_sizes.split(",")[index % 3].strip() if shirt.available_sizes else ""
                line = OrderItem.objects.create(order=order, item=shirt, size=size, quantity=1, status=status["NEW"])
                helmet_line = OrderItem.objects.create(order=order, item=helmet, quantity=1, status=status["NEW"])
                if index >= 2:
                    line = move(line, "ORDERED")
                    helmet_line = move(helmet_line, "ORDERED")
                if index >= 4:
                    line = move(line, "RECEIVED", receipt_location=store.pk)
                if index >= 6:
                    move(line, "DELIVERED", create_loan=True)
                if index == 3:
                    move(helmet_line, "CANCELLED")

    def seed_training(self):
        from servicebook.models import Attendance, StaffAttendance
        from training.models import (
            LibraryBlock,
            LibraryBlockCategory,
            LibraryBlockTag,
            TrainingBlock,
            TrainingBlockMaterial,
            TrainingSession,
            TrainingTemplate,
            TrainingTemplateBlock,
        )
        from training.series import generate_missing, generation_preview
        from training.workflow import linked_service, sync_linked_service

        planner = self.accounts["ausbilder"]
        categories = {
            name: LibraryBlockCategory.objects.create(name=name, color=color, icon=icon)
            for name, color, icon in (
                ("Technik", "#dc2626", "pi-wrench"),
                ("Erste Hilfe", "#16a34a", "pi-heart"),
                ("Spiel & Sport", "#2563eb", "pi-flag"),
                ("Theorie", "#9333ea", "pi-book"),
            )
        }
        tags = {name: LibraryBlockTag.objects.create(name=name) for name in ("Anfänger", "Fortgeschrittene", "Draußen")}
        library = []
        for title, category, minutes, text, tag in (
            ("Knotenkunde", "Technik", 25, "Mastwurf, Schotenstich, Kreuzknoten – mit Wettlauf.", "Anfänger"),
            (
                "Schlauch auslegen",
                "Technik",
                30,
                "C-Schlauch in Buchten auslegen, kuppeln, wieder aufrollen.",
                "Draußen",
            ),
            ("Stabile Seitenlage", "Erste Hilfe", 20, "Ablauf, Kontrolle der Atmung, Notruf 112.", "Anfänger"),
            ("Kübelspritzen-Staffel", "Spiel & Sport", 25, "Zielspritzen auf Kanister im Teamwechsel.", "Draußen"),
            (
                "Fahrzeugkunde LF 10",
                "Theorie",
                30,
                "Beladeplan, Gerätefächer, Sicherheit am Fahrzeug.",
                "Fortgeschrittene",
            ),
        ):
            block = LibraryBlock.objects.create(
                title=title,
                description=text,
                content=f"<p>{text}</p>",
                default_duration_minutes=minutes,
                category=categories[category],
                color=categories[category].color,
                created_by=planner,
            )
            block.tags.add(tags[tag])
            library.append(block)

        def session(code, day, title, status="published", start=time(18, 0), end=time(20, 0), stations=True):
            department = self.departments[code]
            groups = self.groups[code]
            plan = TrainingSession.objects.create(
                title=title,
                date=day,
                start_time=start,
                end_time=end,
                location="Übungshof Feuerwehrhaus",
                department=department,
                created_by=planner,
                status=TrainingSession.Status.DRAFT,
                description="Stationsausbildung mit Wechsel nach Rotationsplan.",
            )
            plan.groups.set(groups)
            TrainingBlock.objects.create(
                session=plan,
                kind="block",
                title="Begrüßung und Sicherheitseinweisung",
                duration_minutes=15,
                start_offset_minutes=0,
                position_order=0,
            )
            if stations and len(groups) > 1:
                picks = library[: len(groups)]
                for round_index in range(len(groups)):
                    offset = 15 + round_index * 30
                    for station_index, source in enumerate(picks):
                        group = groups[(station_index + round_index) % len(groups)]
                        block = TrainingBlock.objects.create(
                            session=plan,
                            kind="station",
                            title=source.title,
                            library_block=source,
                            duration_minutes=25,
                            start_offset_minutes=offset,
                            position_order=station_index,
                            location=f"Station {station_index + 1}",
                            learning_objective=source.description,
                            safety_notes="Helm und Handschuhe tragen." if station_index == 1 else "",
                            color=source.color,
                        )
                        block.groups.add(group)
                        block.instructors.add(self.instructors[station_index % len(self.instructors)])
                        if station_index == 1:
                            TrainingBlockMaterial.objects.create(block=block, item=self.items[code]["hose"], quantity=2)
                            TrainingBlockMaterial.objects.create(block=block, label="Kupplungsschlüssel", quantity=2)
                    TrainingBlock.objects.create(
                        session=plan,
                        kind="transition",
                        title="Wechsel",
                        duration_minutes=5,
                        start_offset_minutes=offset + 25,
                        position_order=99,
                    )
            else:
                block = TrainingBlock.objects.create(
                    session=plan,
                    kind="block",
                    title=library[0].title,
                    library_block=library[0],
                    duration_minutes=60,
                    start_offset_minutes=15,
                    position_order=1,
                )
                block.groups.set(groups)
                block.instructors.add(self.accounts["leitung.kinder"] if code == "kinder" else planner)
            if status != "draft":
                plan.status = TrainingSession.Status.PUBLISHED
                plan.save(update_fields=["status"])
                sync_linked_service(plan)
            return plan

        self.past_trainings = []
        for code in ("mitte", "nord", "kinder"):
            for weeks in (1, 3, 5, 8):
                day = self.today - timedelta(days=7 * weeks + (2 if code == "kinder" else 0))
                plan = session(code, day, f"Übungsdienst {day:%d.%m.}", stations=code != "kinder")
                plan.status = TrainingSession.Status.COMPLETED
                plan.save(update_fields=["status"])
                self.past_trainings.append((code, plan))
            session(
                code, self.today + timedelta(days=4), "Stationsausbildung Wasserförderung", stations=code != "kinder"
            )
            session(code, self.today + timedelta(days=18), "Vorbereitung Leistungsspange (Entwurf)", status="draft")
        cancelled = session("nord", self.today + timedelta(days=11), "Waldbrand-Übung", stations=False)
        cancelled.status = TrainingSession.Status.CANCELLED
        cancelled.save(update_fields=["status"])
        # Weekly series with confirmed preview, as the planner does it in the UI.
        root = session(
            "mitte", self.today + timedelta(days=7), "Wöchentlicher Übungsabend", status="draft", stations=False
        )
        root.recurrence_rule = {"frequency": "WEEKLY", "end_date": str(self.today + timedelta(days=7 * 8))}
        root.save(update_fields=["recurrence_rule"])
        preview = generation_preview(root, [], {}, self.accounts["admin"])
        generate_missing(root, [], {"preview_token": preview["preview_token"]}, self.accounts["admin"])
        template = TrainingTemplate.objects.create(
            title="Vorlage: Erste-Hilfe-Abend",
            start_time=time(18, 0),
            end_time=time(19, 30),
            location="Schulungsraum",
            department=self.departments["mitte"],
            created_by=planner,
        )
        for order, (block, minutes) in enumerate(((library[2], 30), (library[3], 30), (library[4], 30))):
            TrainingTemplateBlock.objects.create(
                template=template,
                title=block.title,
                library_block=block,
                duration_minutes=minutes,
                start_offset_minutes=order * 30,
                position_order=order,
                kind="block",
            )
        # Attendance for completed trainings through their linked service entries.
        for code, plan in self.past_trainings:
            service = linked_service(plan)
            service.operations_manager.add(
                self.accounts[
                    "leitung.mitte" if code == "mitte" else "leitung.nord" if code == "nord" else "leitung.kinder"
                ]
            )
            service.events = "Keine besonderen Vorkommnisse."
            service.save(update_fields=["events"])
            self.attendance(service, code, Attendance, StaffAttendance)

    def attendance(self, service, code, attendance_model, staff_model):
        for member in self.members[code]:
            roll = self.rng.random()
            attendance_model.objects.create(
                person=member, service=service, state="A" if roll < 0.78 else "E" if roll < 0.92 else "F"
            )
        for username in ("betreuer.mitte", "ausbilder") if code == "mitte" else ("betreuer.nord",):
            staff_model.objects.create(
                person=self.accounts[username], service=service, state="A" if self.rng.random() < 0.85 else "E"
            )

    def seed_services(self):
        from servicebook.models import Attendance, Service, StaffAttendance

        # Older service book entries without a training plan (history before the planner).
        topics = [
            "Gerätekunde",
            "Orientierungsmarsch",
            "Erste Hilfe",
            "Knoten und Stiche",
            "Berufsfeuerwehrtag",
            "Wasserförderung",
            "Spieleabend",
            "Brandschutzerziehung",
            "Fahrzeugkunde",
            "Zeltlager-Vorbereitung",
        ]
        for code in ("mitte", "nord"):
            for index, topic in enumerate(topics):
                day = self.today - timedelta(days=70 + 14 * index)
                service = Service.objects.create(
                    start=self.aware(day, time(18, 0)),
                    end=self.aware(day, time(20, 0)),
                    place="Feuerwehrhaus Musterstadt",
                    topic=topic,
                    description="Dienst laut Jahresplan.",
                    department=self.departments[code],
                )
                service.operations_manager.add(self.accounts["leitung.mitte" if code == "mitte" else "leitung.nord"])
                self.attendance(service, code, Attendance, StaffAttendance)

    def seed_communication(self):
        from members.models import EmailMessage, EmailRecipient, MemberList, MemberListEntry

        for code in ("mitte", "nord"):
            department = self.departments[code]
            camp = MemberList.objects.create(
                name="Zeltlager Sommer",
                department=department,
                color="#f59e0b",
                description="Anmeldungen und Teilnahmebeiträge.",
            )
            for index, member in enumerate(self.members[code][:14]):
                MemberListEntry.objects.create(
                    member_list=camp,
                    member=member,
                    checked=index % 3 != 0,
                    notes="Beitrag bezahlt" if index % 3 != 0 else "",
                )
            message = EmailMessage.objects.create(
                sender=self.accounts["kommunikation"],
                subject="Einladung Zeltlager",
                layout="events",
                body_html="<p>Liebe Eltern, das Zeltlager findet vom 12. bis 14. Juni statt.</p>",
                body_text="Liebe Eltern, das Zeltlager findet vom 12. bis 14. Juni statt.",
                recipient_type="all",
                status="sent",
                department=department,
                sent_at=timezone.now() - timedelta(days=9),
            )
            for member in self.members[code]:
                EmailRecipient.objects.create(
                    email_message=message,
                    member=member,
                    email_address=member.email,
                    recipient_name=f"{member.name} {member.lastname}",
                    status="sent",
                    sent_at=message.sent_at,
                )
            message.total_recipients = message.successful_sends = len(self.members[code])
            message.save(update_fields=["total_recipients", "successful_sends"])
        MemberList.objects.create(name="Kreiszeltlager Delegierte", organization_wide=True, color="#0ea5e9")

    def report(self, password):
        from members.models import Member
        from servicebook.models import Service
        from training.models import TrainingSession

        self.stdout.write(
            self.style.SUCCESS(
                f"Demodaten angelegt: {len(self.departments)} Abteilungen, {Member.objects.count()} Mitglieder, "
                f"{Service.objects.count()} Dienste, {TrainingSession.objects.count()} Übungen, {len(self.accounts)} Konten."
            )
        )
        self.stdout.write(f"Konten: {', '.join(self.accounts)}")
        self.stdout.write(f"Gemeinsames Passwort: {password}")
        if self.totp_accounts:
            self.stdout.write(
                "Authenticator hinterlegt für: "
                + ", ".join(self.totp_accounts)
                + " – aktuellen Code mit `python manage.py demo_totp BENUTZER` anzeigen."
            )
