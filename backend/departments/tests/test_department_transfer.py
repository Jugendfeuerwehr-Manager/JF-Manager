import importlib.util
from datetime import date, time, timedelta
from pathlib import Path
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from departments.models import Department
from inventory.models import Item, StorageLocation
from members.models import Group, Member, MemberList, MemberListEntry, Parent
from qualifications.models import Qualification, QualificationType
from servicebook.models import Attendance, Service
from training.models import TrainingSession

spec = importlib.util.spec_from_file_location(
    "department_transfer", Path(__file__).resolve().parents[3] / "ops/tools/department_transfer.py"
)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class DepartmentTransferTests(TestCase):
    def setUp(self):
        self.other = Department.objects.create(name="Andere", code="andere")
        self.group = Group.objects.create(name="Demo")
        self.member = Member.objects.create(name="Fiktiv", group=self.group)
        self.parent = Parent.objects.create(name="Demo-Eltern")
        self.parent.children.add(self.member)
        self.list = MemberList.objects.create(name="Demo", organization_wide=True)
        self.entry = MemberListEntry.objects.create(member_list=self.list, member=self.member, checked=True)
        self.session = TrainingSession.objects.create(
            title="Demo", date=date.today(), start_time=time(18), end_time=time(20)
        )
        self.session.groups.add(self.group)
        self.service = Service.objects.create(
            start=timezone.now() - timedelta(days=30), end=timezone.now(), training_session=self.session
        )
        self.attendance = Attendance.objects.create(person=self.member, service=self.service, state="A")
        qtype = QualificationType.objects.create(name="Demo")
        self.qualification = Qualification.objects.create(member=self.member, type=qtype, date_acquired=date.today())
        self.item = Item.objects.create(name="Demo Jacke")
        self.location = StorageLocation.objects.create(name="Globale Kleiderkammer")
        self.args = dict(
            source="global",
            target="jugendfeuerwehr",
            create_name="Jugendfeuerwehr",
            areas="members,groups,lists,services,training",
        )

    def preview(self, **changes):
        return engine.run_transfer(**(self.args | changes))

    def apply(self, **changes):
        args = self.args | changes
        plan = engine.run_transfer(**args)
        return engine.run_transfer(**args, apply=True, expect=plan["fingerprint"])

    def test_preview_is_read_only_and_finds_dependencies(self):
        plan = self.preview()
        self.assertFalse(plan["conflicts"])
        self.assertFalse(Department.objects.filter(code="jugendfeuerwehr").exists())
        self.assertEqual(plan["counts"]["members.Member"], 1)
        self.assertTrue(self.preview(areas="members")["conflicts"])
        with self.assertRaises(CommandError):
            self.apply(areas="members")
        self.assertFalse(self.member.departments.exists())

    def test_identity_relations_survive_and_inventory_stays_global(self):
        future = Service.objects.create(
            start=timezone.now() + timedelta(days=30), end=timezone.now() + timedelta(days=31)
        )
        self.assertTrue(self.apply()["applied"])
        target = Department.objects.get(code="jugendfeuerwehr")
        self.assertEqual(list(self.member.departments.all()), [target])
        for obj in (self.group, self.list, self.session, self.service, future):
            obj.refresh_from_db()
            self.assertEqual(obj.department_id, target.pk)
        self.assertFalse(self.list.organization_wide)
        self.assertEqual(self.session.revision, 2)
        self.assertTrue(self.parent.children.filter(pk=self.member.pk).exists())
        self.assertEqual(Attendance.objects.get(pk=self.attendance.pk).state, "A")
        self.assertEqual(Qualification.objects.get(pk=self.qualification.pk).member_id, self.member.pk)
        self.assertTrue(MemberListEntry.objects.get(pk=self.entry.pk).checked)
        self.item.refresh_from_db()
        self.location.refresh_from_db()
        self.assertIsNone(self.item.department_id)
        self.assertIsNone(self.location.department_id)
        self.assertEqual(self.preview()["counts"]["members.Member"], 0)
        self.apply()
        self.assertEqual(Member.objects.count(), 1)

    def test_stale_or_missing_preview_refuses_before_creation(self):
        digest = self.preview()["fingerprint"]
        Member.objects.create(name="Weitere Demo")
        with self.assertRaisesMessage(CommandError, "veraltet"):
            engine.run_transfer(**self.args, apply=True, expect=digest)
        with self.assertRaises(CommandError):
            engine.run_transfer(**self.args, apply=True)
        self.assertFalse(Department.objects.filter(code="jugendfeuerwehr").exists())

    def test_multi_department_members_keep_other_memberships(self):
        self.apply()
        self.member.departments.add(self.other)
        self.apply(source="jugendfeuerwehr", target="neu", create_name="Neu")
        self.assertEqual(set(self.member.departments.values_list("code", flat=True)), {"andere", "neu"})

    def test_foreign_incoming_reference_blocks_move(self):
        member = Member.objects.create(name="Andere Demo", group=self.group)
        member.departments.add(self.other)
        with self.assertRaises(CommandError):
            self.apply()
        self.group.refresh_from_db()
        self.assertIsNone(self.group.department_id)

    def test_transaction_rolls_back_on_failure(self):
        digest = self.preview()["fingerprint"]
        real = engine.model

        def fail(label):
            if label == "notifications.InboxItem" and Department.objects.filter(code="jugendfeuerwehr").exists():
                raise RuntimeError("injected failure after writes")
            return real(label)

        with patch.object(engine, "model", side_effect=fail), self.assertRaises(RuntimeError):
            engine.run_transfer(**self.args, apply=True, expect=digest)
        self.assertFalse(Department.objects.filter(code="jugendfeuerwehr").exists())
        self.assertFalse(self.member.departments.exists())
        self.service.refresh_from_db()
        self.assertIsNone(self.service.department_id)

    def test_invalid_input(self):
        for changes in ({"areas": ""}, {"areas": "roles"}, {"target": "global"}, {"source": "missing"}):
            with self.assertRaises(CommandError):
                self.preview(**changes)

    def test_explicit_inventory_selection(self):
        self.apply(areas="inventory")
        self.item.refresh_from_db()
        self.location.refresh_from_db()
        self.assertEqual(self.item.department.code, "jugendfeuerwehr")
        self.assertEqual(self.location.department.code, "jugendfeuerwehr")

    def test_inventory_foreign_stock_location_blocks_move(self):
        from inventory.models import Stock

        self.location.department = self.other
        self.location.save()
        Stock.objects.create(item=self.item, location=self.location)
        with self.assertRaises(CommandError):
            self.apply(areas="inventory")
        self.item.refresh_from_db()
        self.assertIsNone(self.item.department_id)

    def test_foreign_material_blocks_inventory_transfer(self):
        from training.models import TrainingBlock, TrainingBlockMaterial

        self.session.department = self.other
        self.session.save()
        block = TrainingBlock.objects.create(session=self.session, title="Demo")
        TrainingBlockMaterial.objects.create(block=block, item=self.item)
        with self.assertRaises(CommandError):
            self.apply(areas="inventory")

    def test_owned_inbox_moves_without_changing_recipients(self):
        from notifications.models import InboxItem

        item = InboxItem.objects.create(kind="demo", object_type="training.trainingsession", object_id=self.session.pk)
        self.apply()
        item.refresh_from_db()
        self.assertEqual(item.department.code, "jugendfeuerwehr")
