"""PART-04.5: staffing templates, independent copies into services, exercise templates and series."""

from datetime import timedelta

from django.contrib.auth.models import Permission
from django.utils import timezone

from departments.models import UserDepartmentRole
from participation import service
from participation.copying import copy_configuration
from participation.models import Registration, SessionParticipation, Slot, StaffingTemplate, TemplateParticipation
from qualifications.models import QualificationType
from training.copying import copied_files, session_to_template, template_to_session

from .helpers import configure, make_session
from .test_staff_api import StaffApiBase, url

TEMPLATES = "/api/v1/participation/templates/"


def guard_body(qtype_id):
    return {
        "mode": "opt_in",
        "eligibility": {},
        "waitlist_mode": "manual",
        "extra_places": 1,
        "slots": [
            {
                "label": "Wachführung",
                "min": 1,
                "max": 1,
                "rule": {
                    "v": 1,
                    "match": "all",
                    "rules": [{"kind": "qualification", "op": "has_any", "values": [qtype_id]}],
                },
            },
            {"label": "Truppmann/-frau", "min": 2, "max": 2, "rule": {}},
        ],
    }


class TemplateApiTests(StaffApiBase):
    def setUp(self):
        super().setUp()
        self.qtype = QualificationType.objects.create(name="Gruppenführer")

    def create(self, user=None, **extra):
        client = self.as_user(user) if user else self.client
        body = {"name": "Brandsicherheitswache", "department": self.dept.pk, "body": guard_body(self.qtype.pk), **extra}
        return client.post(TEMPLATES, body, format="json")

    def apply(self, template_id, session=None, user=None):
        session = session or self.session
        client = self.as_user(user) if user else self.client
        revision = service.participation_for(session)[0].revision
        return client.post(
            url(session, "apply-template/"), {"template": template_id, "revision": revision}, format="json"
        )

    def test_create_list_and_apply_as_independent_copy(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.content)
        template_id = response.json()["id"]
        listing = self.client.get(TEMPLATES, {"department": self.dept.pk}).json()["results"]
        self.assertEqual([t["name"] for t in listing], ["Brandsicherheitswache"])
        self.assertEqual(listing[0]["slots"][0], {"label": "Wachführung", "min": 1, "max": 1})
        response = self.apply(template_id)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body["mode"], body["waitlist_mode"], body["max_participants"]), ("opt_in", "manual", 4))
        self.assertEqual([s["label"] for s in body["slots"]], ["Wachführung", "Truppmann/-frau"])
        self.assertEqual(body["template_source"], {"id": template_id, "name": "Brandsicherheitswache"})
        # changing the template does not touch the service
        template = StaffingTemplate.objects.get(pk=template_id)
        template.body["slots"][0]["label"] = "Geändert"
        template.save()
        self.assertEqual(Slot.objects.filter(participation__session=self.session).first().label, "Wachführung")

    def test_save_from_session_snapshot(self):
        participation = configure(self.session, mode="assignment", max_participants=3)
        Slot.objects.create(participation=participation, label="Melder", min_count=0, max_count=3)
        response = self.create(body=None, session=self.session.pk, name="Aus Dienst")
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()["body"]
        self.assertEqual(
            (body["mode"], body["slots"][0]["label"], body["max_participants"]), ("assignment", "Melder", None)
        )

    def test_deleted_qualification_is_reported_as_warning(self):
        template_id = self.create().json()["id"]
        self.qtype.delete()
        response = self.apply(template_id)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(response.json()["warnings"]), 1)
        self.assertIn("gibt es nicht mehr", response.json()["warnings"][0])
        self.assertEqual(response.json()["slots"][0]["rule"], {})

    def test_taken_positions_block_applying(self):
        participation = configure(self.session, mode="opt_in", max_participants=1)
        slot = Slot.objects.create(participation=participation, label="Alt", max_count=1)
        Registration.objects.create(
            session=self.session,
            member=self.mia,
            state="registered",
            slot=slot,
            source="staff",
            state_changed_at=timezone.now(),
        )
        response = self.apply(self.create().json()["id"])
        self.assertEqual((response.status_code, response.json()["code"]), (422, "positions_taken"))

    def test_stale_revision(self):
        template_id = self.create().json()["id"]
        response = self.client.post(
            url(self.session, "apply-template/"), {"template": template_id, "revision": 7}, format="json"
        )
        self.assertEqual(response.status_code, 409)

    def test_archive_hides_from_list_and_update_uses_version(self):
        template = self.create().json()
        archived = self.client.post(f"{TEMPLATES}{template['id']}/archive/").json()
        self.assertTrue(archived["archived"])
        self.assertEqual(self.client.get(TEMPLATES).json()["results"], [])
        self.assertEqual(len(self.client.get(TEMPLATES, {"archived": "1"}).json()["results"]), 1)
        self.client.post(f"{TEMPLATES}{template['id']}/unarchive/")
        stale = self.client.put(
            f"{TEMPLATES}{template['id']}/", {"name": "Neu", "department": self.dept.pk, "version": 1}, format="json"
        )
        self.assertEqual(stale.status_code, 409)
        fresh = self.client.put(
            f"{TEMPLATES}{template['id']}/", {"name": "Neu", "department": self.dept.pk, "version": 3}, format="json"
        )
        self.assertEqual((fresh.status_code, fresh.json()["name"]), (200, "Neu"))

    def test_validation(self):
        bad = guard_body(self.qtype.pk)
        bad["slots"][0]["min"] = 5
        self.assertEqual(self.create(body=bad).status_code, 400)
        self.assertEqual(self.create(name="<b>x</b>").status_code, 400)
        self.assertEqual(
            self.create(body={"mode": "opt_out", "slots": [{"label": "A", "min": 0, "max": 1}]}).status_code, 400
        )

    def test_department_and_organisation_scope(self):
        other_template = StaffingTemplate.objects.create(
            name="Fremd", department=self.other, body=guard_body(self.qtype.pk)
        )
        org_template = StaffingTemplate.objects.create(name="Org", department=None, body=guard_body(self.qtype.pk))
        names = [t["name"] for t in self.client.get(TEMPLATES).json()["results"]]
        self.assertEqual(names, ["Org"])
        self.assertEqual(self.client.get(f"{TEMPLATES}{other_template.pk}/").status_code, 404)
        self.assertEqual(self.apply(other_template.pk).status_code, 404)
        self.assertEqual(self.apply(org_template.pk).status_code, 200)
        # department planners may not create or change organisation templates
        self.assertEqual(self.create(department=None).status_code, 403)
        self.assertEqual(self.client.post(f"{TEMPLATES}{org_template.pk}/archive/").status_code, 403)
        self.assertEqual(self.create(user=self.other_planner).status_code, 403)
        # organisation-wide planners may
        org_planner = type(self.planner).objects.create_user("org-planer")
        org_planner.user_permissions.add(
            Permission.objects.get(codename="can_manage_training"),
            Permission.objects.get(codename="can_access_all_departments"),
        )
        UserDepartmentRole.objects.create(user=org_planner, department=self.dept)
        self.assertEqual(self.create(user=org_planner, department=None, name="Org neu").status_code, 201)

    def test_permissions(self):
        self.assertEqual(self.as_user(self.portal).get(TEMPLATES).status_code, 403)
        self.assertEqual(self.create(user=self.portal).status_code, 403)
        self.assertEqual(self.as_user(self.reader).get(TEMPLATES).status_code, 403)
        template_id = self.create().json()["id"]
        self.assertEqual(self.apply(template_id, user=self.reader).status_code, 403)
        self.assertEqual(self.apply(template_id, user=self.other_planner).status_code, 403)


class TemplateCopyTests(StaffApiBase):
    def setUp(self):
        super().setUp()
        self.participation = configure(self.session, mode="opt_in", max_participants=3, extra_places=1)
        Slot.objects.create(participation=self.participation, label="Trupp", min_count=1, max_count=2)

    def test_series_occurrence_gets_its_own_positions(self):
        target = make_session(self.dept, day=self.day + timedelta(days=7), title="Folgetermin")
        copy = copy_configuration(self.session, target)
        self.assertEqual((copy.extra_places, [s.label for s in copy.slots.all()]), (1, ["Trupp"]))
        Slot.objects.filter(participation=copy).update(label="Nur Kopie")
        self.assertEqual(self.participation.slots.get().label, "Trupp")

    def test_exercise_template_round_trip_is_independent(self):
        with copied_files() as files:
            training_template = session_to_template(self.session, self.planner, files)
        stored = TemplateParticipation.objects.get(template=training_template)
        self.assertEqual(stored.body["slots"][0]["label"], "Trupp")
        Slot.objects.filter(participation=self.participation).update(label="Später geändert")
        with copied_files() as files:
            new_session = template_to_session(training_template, self.day + timedelta(days=14), self.planner, files)
        copy = SessionParticipation.objects.get(session=new_session)
        self.assertEqual(
            (copy.mode, [s.label for s in copy.slots.all()], copy.max_participants), ("opt_in", ["Trupp"], 3)
        )

    def test_staffing_template_into_exercise_template(self):
        template = StaffingTemplate.objects.create(name="Wache", department=self.dept, body=guard_body(0))
        template.body["slots"][0]["rule"] = {}
        template.save()
        with copied_files() as files:
            training_template = session_to_template(self.session, self.planner, files)
        path = f"/api/v1/participation/training-templates/{training_template.pk}/"
        response = self.client.put(path, {"staffing_template": template.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([s["label"] for s in response.json()["slots"]], ["Wachführung", "Truppmann/-frau"])
        self.assertEqual(self.as_user(self.other_planner).get(path).status_code, 403)
        with copied_files() as files:
            new_session = template_to_session(training_template, self.day + timedelta(days=21), self.planner, files)
        copy = SessionParticipation.objects.get(session=new_session)
        self.assertEqual((copy.template_source_id, copy.waitlist_mode), (template.pk, "manual"))
